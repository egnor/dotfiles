# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Dan Egnor's personal config — both per-user dotfiles and machine-level configuration (system tweaks, nginx, etc.). Driven by [pyinfra](https://pyinfra.com/): `deploy.py` is the entrypoint, included files do the work.

## How to apply changes

```
pyinfra @local deploy.py            # this machine, no SSH
pyinfra @local deploy.py --dry      # preview without applying
pyinfra eacs.io deploy.py           # single remote host over SSH
pyinfra inventory.py deploy.py      # whole fleet (when an inventory.py is present)
```

The first positional arg is the inventory — `@local` is the local connector, a hostname is treated as an inline single-host inventory, or you can write an `inventory.py`. Operations files run on the controller; pyinfra ships file content over the wire as needed and never copies the deploy scripts themselves.

## Layout

Each top-level subdirectory is one *area*: a `setup.py` plus a `files/` directory containing the content that script puts on the target.

- `deploy.py` — entrypoint. Just a list of `local.include(...)` calls, one per area.
- `nginx/` — host-specific (gated on `Hostname == "egnor-2020"`). Manages `/etc/nginx/nginx.conf` whole-file, the contents of `/etc/nginx/sites-enabled/` via `files.sync(delete=True)`, an `acme-challenge.conf` snippet under `/etc/nginx/snippets/`, and the `/var/www/letsencrypt` ACME webroot. The Debian sites-available/sites-enabled split is dropped — files go directly to sites-enabled/. Every `:443` server block includes the ACME snippet so all certs can use the same shared webroot.
- `certbot/` — host-specific (same gate). Manages `/etc/letsencrypt/cli.ini` (sets `authenticator = webroot` so certbot never edits nginx) and a `renewal-hooks/deploy/reload-nginx` script. The package's `certbot.timer` handles renewal; we just configure what it does.
- `postfix/` — host-specific (`Hostname == "egnor-2020"`). Manages `/etc/postfix/{main.cf, master.cf, virtual, aliases_regexp}` and `/etc/postfix/sasl/smtpd.conf`, plus `/etc/aliases` and `/etc/mailname`. Triggers `postmap virtual` / `newaliases` on source change. The cyrus-sasl password DB (`sasldb2`) is NOT in the repo (live secrets, plaintext-equivalent due to CRAM-MD5/DIGEST-MD5) — see "SASL password workflow" below. `/etc/sasldb2` is a symlink to `/var/spool/postfix/etc/sasldb2` (the chroot copy) so cyrus-sasl tools, which default to `/etc/sasldb2`, target the same file postfix reads.
- `opendkim/` — host-specific (same gate). Manages `/etc/opendkim.conf` and the three text tables under `/etc/dkimkeys/` (`signing.table`, `key.table`, `trusted.hosts`). The `.private` keys stay out-of-band (live secrets). Wired into postfix as a milter via `local:opendkim/opendkim.sock` (a unix socket inside postfix's chroot).
- `netdata/` — Netdata config. Parent vs child role picked by hostname (`egnor-2020` is the parent; everywhere else is a child streaming up to it). Manages `netdata.conf` + `stream.conf` only; `claim.conf` (Cloud token) and the package install are out-of-band. No-ops if `/etc/netdata` doesn't exist.
- `user/` — per-user dotfiles. `setup.py` symlinks every leaf under `user/files/` into the target's `$HOME`. A "leaf" is a regular file, a symlink, or a directory containing `.git` (the latter two are linked as a unit, not recursed into). Probes `~/source/dotfiles` and `~/dotfiles` for an existing checkout (and clones to `~/dotfiles` otherwise).
- `tweaks/` — root-owned `/etc` / systemd drop-ins, gated on facts (`LinuxName`, etc.) so the file is safe to run on any host — inapplicable tweaks just skip. Each tweak: `files.put` followed by `systemd.daemon_reload` + `systemd.service` chained via `_if=op.did_change` so reloads only happen on real changes.

## Adding a new HTTPS site

1. Make the document root if needed: `sudo mkdir -p /home/egnor/www-<name> && sudo chown egnor:egnor /home/egnor/www-<name>`.
2. Add a `:443` `server { ... }` block to a file under `nginx/files/sites-enabled/`. Include the ACME snippet at the top: `include /etc/nginx/snippets/acme-challenge.conf;`. Reference `/etc/letsencrypt/live/<cert-name>/{fullchain,privkey}.pem`.
3. Add a corresponding `:80` block doing `return 301 https://<domain>$request_uri;` (preserve `$request_uri` so HTTP-01 redirects work).
4. Cert doesn't exist yet, so step 2's `:443` block would crash nginx if deployed now — temporarily comment it out, deploy `:80` only with `pyinfra @local deploy.py`, then issue: `sudo certbot certonly --cert-name <name> -d <domain> [-d <alias>]...` (`cli.ini` supplies the rest, including the shared `webroot-path`). To add a name to an existing cert, repeat the full `-d` list with the new name appended.
5. Uncomment the `:443` block; `pyinfra @local deploy.py` again.

If a `:80` or `:443` server uses server-level `return` / `proxy_pass` / aggressive `location ~` regexes that would short-circuit the snippet, restructure the redirect into a `location / { return ...; }` so the snippet's `^~` prefix match wins.

Renewal happens automatically via `certbot.timer` (twice daily). The `reload-nginx` deploy hook reloads nginx after any successful renewal.

## Migrating an existing cert from `--nginx` to `--webroot` auth

Pre-`certbot/` certs were issued with the nginx authenticator, which still tries to edit nginx config files at renewal time. Because the ACME snippet is in every `:443` server block, the migration is uniform across all certs:

```
sudo certbot reconfigure --cert-name <cert-name> --webroot
```

`reconfigure` performs a staging-style validation against the new config and only commits to `/etc/letsencrypt/renewal/<cert-name>.conf` if it passes. List current certs with `sudo certbot certificates`. Migrating opportunistically as you next touch each site is fine — unmigrated certs continue to renew with `--nginx` until you flip them.

## SASL password workflow (postfix submission auth)

The cyrus-sasl password DB used by `smtpd_sasl_auth_enable=yes` lives at `/var/spool/postfix/etc/sasldb2` (postfix is chrooted, so it sees `/etc/sasldb2` from inside its spool). `/etc/sasldb2` is a symlink to that chroot path so the cyrus-sasl admin tools (`saslpasswd2`, `sasldblistusers2`), which default to `/etc/sasldb2`, target the same file postfix actually reads.

The DB itself contains live, plaintext-equivalent passwords (because the mech list includes CRAM-MD5/DIGEST-MD5, which require the server to know the cleartext) and is therefore *not* in the repo. To add or rotate:

```
sudo saslpasswd2 -c -u $(sudo postconf -h myhostname) <user>     # add or update
sudo saslpasswd2 -d -u $(sudo postconf -h myhostname) <user>     # delete
sudo sasldblistusers2                                            # list (no passwords shown)
```

The realm flag (`-u`) must match `myhostname` from `main.cf` — clients authenticate as `<user>@<realm>`. No postfix reload or pyinfra deploy is needed; sasldb is read per-authentication.

## Adding a new area

1. Create `<area>/setup.py` and `<area>/files/`.
2. Gate the work on whatever fact applies (`Hostname`, `LinuxName`, group membership) so other hosts no-op cleanly.
3. Reference content with `src="<area>/files/<name>"` (resolved from the deploy directory, which is the repo root when running `pyinfra ... deploy.py`).
4. Files that should look identical in repo and on disk get a `# Managed by pyinfra. Source: ...` header in the source file itself — no template needed. Use `files.template` (Jinja) only if you need real interpolation.
5. Wire follow-up actions (reload/restart) with `_if=op.did_change` (one op) or `_if=any_changed(op1, op2, ...)` (multiple).
6. Add `local.include("<area>/setup.py")` to `deploy.py`.

## Gating idioms

- OS family: `if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):`
- Specific host: `if host.get_fact(Hostname) == "egnor-2020":`
- Group membership: `if "system_admin" in host.groups:`

We deliberately don't maintain a central host-config dict; each area's `setup.py` checks for the hosts it should run on.

## Tooling expectations

`user/files/.config/mise/config.toml` pins the tools the `.zshrc` expects to find on PATH (`fd`, `gh`, `lazygit`, `neovim`, `node`, `python`, `ripgrep`, `@github/copilot-language-server`). `mise` is activated from `.zshrc` if present. If you add a shell helper that depends on a new binary, add it to the mise config in the same change.

The repo-root `mise.toml` and `pyproject.toml`/`uv.lock` set up the Python env that runs pyinfra itself (via `uv sync`).

Neovim config under `user/files/.config/nvim/` is a LazyVim starter — plugins are managed by lazy.nvim at runtime, not vendored here.
