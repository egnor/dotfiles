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
- `postfix/` — host-specific (`Hostname == "egnor-2020"`). Manages `/etc/postfix/{main.cf, master.cf, virtual, aliases_regexp}` and `/etc/postfix/sasl/smtpd.conf`, plus `/etc/mailname`. Triggers `postmap virtual` on source change. `/etc/aliases` is shipped as an inert comment-only file (postfix's `alias_maps` points only at `aliases_regexp`, and that file's `/.*/ egnor@ofb.net` catch-all already routes every local recipient); the corresponding `/etc/aliases.db` is actively removed by the deploy so nothing stale lingers. The cyrus-sasl password DB (`sasldb2`) is NOT in the repo (live secrets, plaintext-equivalent due to CRAM-MD5/DIGEST-MD5) — see "SASL password workflow" below. `/etc/sasldb2` is a symlink to `/var/spool/postfix/etc/sasldb2` (the chroot copy) so cyrus-sasl tools, which default to `/etc/sasldb2`, target the same file postfix reads.
- `opendkim/` — host-specific (same gate). Manages `/etc/opendkim.conf` and the three text tables under `/etc/dkimkeys/` (`signing.table`, `key.table`, `trusted.hosts`). The `.private` keys stay out-of-band (live secrets). Wired into postfix as a milter via `local:opendkim/opendkim.sock` (a unix socket inside postfix's chroot).
- `postsrsd/` — host-specific (same gate). Manages `/etc/default/postsrsd` for the Sender Rewriting Scheme daemon. Wired into postfix via `{sender,recipient}_canonical_maps = tcp:127.0.0.1:{10001,10002}` so mail FORWARDED through this host (alias_maps / virtual_alias_maps re-injection) gets its envelope-from rewritten to an SRS-encoded `@eacs.io` address — preserves SPF alignment at the next hop without forging the original sender. `SRS_EXCLUDE_DOMAINS` lists every domain whose envelope-from should be left alone: our local mail-receiving domains (eacs.io, approximately.competent.services, blackletterlabs.com, seventeengames.com) PLUS `ofb.net`, because this host is ofb's outbound :25 relay (GCE blocks outbound :25 from ofb), and ofb.net's SPF already authorizes 104.200.25.248 directly. Other ofb-hosted domains (tattoobag.com, etc.) are NOT excluded — when those appear in envelope-from here, it's via ofb-side forwarding of probably-spoofed mail, which is exactly what SRS should rewrite. The HMAC secret at `/etc/postsrsd.secret` is package-generated on first install (mode 0600, owner=postsrs) and stays out of the repo. `postsrsd/` is included in `deploy.py` BEFORE `postfix/` so postsrsd is configured + running before postfix reload activates the canonical_maps lookup.
- `dns/` — host-specific (`Hostname == "egnor-2020"`). Knot DNS authoritative server. Primary for user-owned zones, with source-of-truth zone files at `/etc/knot/zones/` managed from this repo and Hurricane Electric (`ns{1..5}.he.net`) as the AXFR-pulling secondary, registered per-zone at `dns.he.net`. Replaces BIND9 — `dns/setup.py` stops and disables `named.service` so Knot can claim port 53. Also drops in `DNSStubListener=no` for systemd-resolved (and repoints `/etc/resolv.conf` at the non-stub `/run/systemd/resolve/resolv.conf` that resolved still maintains) so the stub on `127.0.0.53` doesn't conflict with Knot's `0.0.0.0:53` bind. Knot's mutable state (journals, slave-zone caches) stays at the package default `/var/lib/knot/`; primary-zone files in `knot.conf` use absolute paths into `/etc/knot/zones/`. Knot bumps SOA serials itself (`serial-policy: unixtime`, `zonefile-load: difference-no-serial`, `journal-content: all`) so primary zone files can keep `1` as the serial forever.
- `netdata/` — Netdata config. Parent vs child role picked by hostname (`egnor-2020` is the parent; everywhere else is a child streaming up to it). On Linux, manages `netdata.conf` + `stream.conf` (config dir `/etc/netdata`), plus the `go.d/` and `health.d/` overrides, and installs `smartmontools` so the go.d `smartctl` collector reports SMART disk health on physical hosts; alerts are evaluated on the parent (`files.parent/health.d/smartctl.conf`) since children run with `[health] enabled = no`. **FreeBSD/OPNsense** (gated on `Os == "FreeBSD"`, e.g. `onerouting`, config dir `/usr/local/etc/netdata`) is a special child: the `os-netdata` plugin re-renders `netdata.conf` from a Jinja template on every GUI apply, so we DON'T manage it there — only `stream.conf` (outside the plugin's template scope) is pushed, reusing the Linux child's key + destination. Consequence: the child-side `netdata.conf` tweaks (`[health] enabled = no`, `is ephemeral node`) aren't applied — health is evaluated locally too (harmless duplicate of the parent), and the node is non-ephemeral (fine for an always-on router). Run standalone: `pyinfra onerouting.internal netdata/setup.py` (connects as the `egnor` user + sudo; that user MUST have a `/bin/sh` login shell, since root's shell is the OPNsense console-menu wrapper that routes `-c` through csh and breaks pyinfra). `claim.conf` (Cloud token) and the package install are out-of-band. No-ops if the config dir doesn't exist.
- `user/` — per-user dotfiles, gated on `Os == "Linux"` (skips FreeBSD/OPNsense and other non-Linux). `setup.py` symlinks every leaf under `user/files-linux/` into the target's `$HOME`, plus `user/files-linux-modern/` on Ubuntu 20.04+ (tools whose prebuilt binaries need a recent glibc — mise conf.d, the LazyVim nvim config). `user/copy-files/` holds the few files that must be copied not linked (e.g. `.forward`). A "leaf" is a regular file, a symlink, or a directory containing `.git` (the latter two are linked as a unit, not recursed into). Probes `~/source/dotfiles` and `~/dotfiles` for an existing checkout (and clones to `~/dotfiles` otherwise).
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

The realm flag (`-u`) is just a namespace inside sasldb — it does not have to match `myhostname` or any DNS name. Clients authenticate as `<user>@<realm>`, and cyrus-sasl splits on `@` to look up the entry. If the client sends a bare username with no `@`, the default realm is `$myhostname` (postfix's cyrus-sasl integration), so picking the realm to match `myhostname` is *one* sensible convention but not a requirement. In practice the entries on this host are stored at the user's own domain (e.g. `egnor@ofb.net`, `shop@seventeengames.com`) so they survive `myhostname` changes untouched. No postfix reload or pyinfra deploy is needed; sasldb is read per-authentication.

## Adding a zone to the Knot nameserver

Most zones in `dns/files/zones/` are the boilerplate `apex SOA + $INCLUDE _common.inc` shape: apex A/AAAA point at this host (`104.200.25.248`, the two IPv6 addresses), and a single-label `* CNAME @` wildcard covers everything else. To add another zone in that shape:

1. Create `dns/files/zones/<zone>.zone` with this content (swap the `$ORIGIN`):

   ```
   ; Managed by pyinfra. Source: dns/files/zones/<zone>.zone
   $ORIGIN <zone>.
   $TTL 1h

   @ SOA ns1.eacs.io. hostmaster.eacs.io. ( 1 1h 15m 7d 1h )

   $INCLUDE /etc/knot/zones/_common.inc
   ```

2. Add the zone name to the list in `dns/files/knot.conf`.
3. `pyinfra @local deploy.py`. Knot reloads; check `journalctl -u knot --since "1 minute ago"` for parse errors.
4. **Validate** before pointing real traffic at it:

   ```
   dig @127.0.0.1 <zone> SOA
   dig @127.0.0.1 something.<zone> A    # should resolve via wildcard
   ```

5. If the zone needs MX, SPF, DMARC, DKIM, or non-wildcard subdomains, put them *after* the `$INCLUDE` line — explicit records override the wildcard. See `eacs.io.zone` (mail-receiving) and `teamleftout.org.zone` (Google Workspace + custom records) for examples of the deviation patterns.

The SOA serial in the file stays `1` forever. Knot detects content changes via `zonefile-load: difference-no-serial` and writes a real serial (Unix timestamp) into its journal at `/var/lib/knot/`.

### DMARC records — the wildcard hazard, and how to add a real policy

The `* CNAME @` wildcard in `_common.inc` silently catches `_dmarc.<zone>` queries on every zone served from here, CNAMEing them to the apex (which carries SPF TXT, not DMARC TXT). DMARC verifiers see a non-DMARC TXT and conclude "no policy" — so all zones served from this host are effectively DMARC-unprotected *unless* they ship an explicit `_dmarc TXT`. Adding any record at `_dmarc.<zone>` suppresses the wildcard for that name (DNS wildcards don't expand for names that have other records).

Reporting is consolidated at **Postmark** (free DMARC processor); each zone needs its own per-zone identifier registered there. To migrate or add a zone:

1. Log in to Postmark's DMARC dashboard, "Add domain", enter `<zone>`. Postmark issues an `rua` token like `re+xxxxxxxxxxxx@dmarc.postmarkapp.com` unique to that domain.
2. Add `_dmarc` to the zone file *after* the `$INCLUDE` line (so the wildcard CNAME for that name is overridden):

   ```
   _dmarc 1h TXT "v=DMARC1; p=quarantine; pct=100; rua=mailto:re+xxxxxxxxxxxx@dmarc.postmarkapp.com; sp=none; aspf=r;"
   ```

   Style notes (matching the existing Postmark-using domains): `p=quarantine` for enforcement, `sp=none` to leave subdomain policy permissive, `aspf=r` for relaxed SPF alignment (since SRS-rewriting may break strict alignment across forwarders).

3. `pyinfra @local deploy.py` to reload Knot and propagate to HE secondaries.
4. Send a couple of test messages and check Postmark's dashboard the next day — it aggregates reports from receiving MTAs (Gmail/Yahoo/Microsoft) into a single view.

The `eacs.io` zone currently uses `rua=mailto:info@eacs.io` (raw reports land in the local mailbox) — migrate it to Postmark like any other zone when convenient.

`ofb.net`'s DMARC (`v=DMARC1;p=none;` with no `rua`) lives in ofb's own DNS config (not this repo) — it would be updated via `reference/ofb_config_bind/config.sh` on the ofb side, not here.

## BIND9 → Knot first-time cutover

The Knot config in `dns/setup.py` also stops `named.service` (BIND9), since the two can't share port 53. Before the cutover, BIND was running here as `ns2.ofb.net` — secondary for ofb.net's then ~124 zones, slaving from `104.197.242.163`. OFB has since been weaned off rely on egnor-2020 for slave service.

First-time procedure on `egnor-2020`:

1. **Dry-run** to preview what pyinfra will do: `pyinfra @local deploy.py --dry`. Confirm the BIND stop / Knot start ops appear once and only once.
2. **Validate the config offline** before pyinfra reloads Knot for real: `sudo knotc -c dns/files/knot.conf conf-check`. Expect `Configuration is valid`. (Validating zone files needs `kzonecheck`, which is not packaged on Ubuntu — `named-checkzone` from BIND9 works as a stand-in since the syntax is compatible.)
3. **Deploy**: `pyinfra @local deploy.py`. There's a 1–2 second window between BIND stopping and Knot binding where port 53 is unanswered; ns1.ofb.net continues to serve the slaved zones from its end, so external resolvers see the zones as briefly less-redundant rather than down.
4. **Smoke test** after deploy:

   ```
   dig @127.0.0.1 eacs.io SOA          # should show ns1.eacs.io. (primary)
   dig @127.0.0.1 ofb.net SOA          # should show ofb.net. (slaved from ns1.ofb.net)
   sudo knotc zone-status              # primary + secondary zones all "open"
   journalctl -u knot -n 50            # look for AXFR completed lines, no errors
   ```

5. `/etc/bind/` is left in place but inert (the package isn't removed; the unit is disabled). Clean up `apt purge bind9` later once you're confident Knot is stable.
6. **Reboot, or restart long-running daemons that cache resolver state.** Switching `/etc/resolv.conf` from systemd-resolved's stub to the non-stub file invalidates the cached resolver address (127.0.0.53) inside any already-running process. glibc doesn't always notice the symlink target change. Most-affected daemons here: `postfix` (mail deferred with "Name service error … try again"), `opendkim` (DKIM lookups), `netdata` (HTTP-check alerts firing for hostnames it can't resolve). `systemctl restart postfix opendkim netdata` fixes them; a reboot catches everything plus validates cold-boot of the new config.

## Cutover: pointing a zone at the egnor-2020 nameserver

Once the zone file is live in Knot (previous section), flipping the actual delegation is an external action — not automatable from this repo. **Note:** ten zones (`teamleftout.org`, the six puzzlehunt zones, `nutrimatic.org`, `dan.egnor.name`, `egnor.me`) appear in both Knot's primary list *and* in ofb's `master.conf`. While the duplicate-mastering condition exists, ns1.ofb.net and ns2.ofb.net answer with different content (different NS sets, no MX, no `_http._tcp` SRV records on the Knot side per `_common.inc`). Externally resolvers see a "lame delegation" — usually harmless, but worth closing out promptly via step 2 below.

1. **Register the secondary at dns.he.net.** Log in to Hurricane Electric DNS, "Add new zone", enter `<zone>`. HE will start AXFR-pulling from this host on demand; the `he_xfr` ACL in `knot.conf` is already open to their 10 IPs. Verify HE has the zone:

   ```
   dig @ns1.he.net <zone> SOA
   ```

2. **Remove the zone from ofb's master.** For the ten zones currently on both sides: edit `reference/ofb_config_bind/config.sh` to drop the corresponding `master <zone> ...` line, re-run the script to regenerate `master.conf` and `slave.conf`, `rndc reload` on ofb. After this, ofb's ns1 stops answering for the zone; only Knot here (and HE.net once step 1 is done) are authoritative.
3. **Update NS records at the registrar.** Replace the existing nameservers with:

   ```
   ns1.eacs.io.
   ns1.he.net.   ns2.he.net.   ns3.he.net.   ns4.he.net.   ns5.he.net.
   ```

   For zones whose registrar is Porkbun or Squarespace (most of ours), this is a single form field per zone.
4. **Glue records (eacs.io only).** Because `ns1.eacs.io` is *in* the `eacs.io` zone it serves, the `.io` registrar (Squarespace) needs explicit "host" records: `ns1.eacs.io = 104.200.25.248` plus the two IPv6 addresses. Without glue, resolvers can't find ns1.eacs.io to ask it for eacs.io. No glue is needed for other zones — they just list ns1.eacs.io and let resolvers chase it through `.io`.

TTLs at the apex are 1h, so propagation is fast. The old NS set keeps answering until its parent-TLD TTL expires (typically 1–2 days), so a brief overlap where both servers answer correctly is normal and safe.

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

`user/files-linux/.config/mise/config.toml` pins the tools the `.zshrc` expects to find on PATH (`fd`, `gh`, `lazygit`, `neovim`, `node`, `python`, `ripgrep`, `@github/copilot-language-server`). `mise` is activated from `.zshrc` if present. If you add a shell helper that depends on a new binary, add it to the mise config in the same change.

The repo-root `mise.toml` and `pyproject.toml`/`uv.lock` set up the Python env that runs pyinfra itself (via `uv sync`).

Neovim config under `user/files-linux-modern/.config/nvim/` is a LazyVim starter — plugins are managed by lazy.nvim at runtime, not vendored here.
