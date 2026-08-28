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

- `deploy.py` — entrypoint. A list of `local.include(...)` calls, one per area, alphabetical except for the trailing `postsrsd/` → `postfix/` pair, which is order-dependent (see `postsrsd/` below). Keep it that way when adding an area.
- `nginx/` — host-specific (gated on `Hostname == "egnor-2020"`). Manages `/etc/nginx/nginx.conf` whole-file, the contents of `/etc/nginx/sites-enabled/` via `files.sync(delete=True)`, an `acme-challenge.conf` snippet under `/etc/nginx/snippets/`, and the `/var/www/letsencrypt` ACME webroot. The Debian sites-available/sites-enabled split is dropped — files go directly to sites-enabled/. Every `:443` server block includes the ACME snippet so all certs can use the same shared webroot.
- `certbot/` — host-specific (same gate). Manages `/etc/letsencrypt/cli.ini` (sets `authenticator = webroot` so certbot never edits nginx) and a `renewal-hooks/deploy/reload-nginx` script. The package's `certbot.timer` handles renewal; we just configure what it does.
- `postfix/` — host-specific (`Hostname == "egnor-2020"`). Manages `/etc/postfix/{main.cf, master.cf, virtual, aliases_regexp}` and `/etc/postfix/sasl/smtpd.conf`, plus `/etc/mailname`. Triggers `postmap virtual` on source change. `/etc/aliases` is shipped as an inert comment-only file (postfix's `alias_maps` points only at `aliases_regexp`, and that file's `/.*/ egnor@ofb.net` catch-all already routes every local recipient); the corresponding `/etc/aliases.db` is actively removed by the deploy so nothing stale lingers. The cyrus-sasl password DB (`sasldb2`) is NOT in the repo (live secrets, plaintext-equivalent due to CRAM-MD5/DIGEST-MD5) — see "SASL password workflow" below. `/etc/sasldb2` is a symlink to `/var/spool/postfix/etc/sasldb2` (the chroot copy) so cyrus-sasl tools, which default to `/etc/sasldb2`, target the same file postfix reads. Also pins postfix's chrooted resolver: a drop-in at `/etc/systemd/system/postfix@.service.d/fix-chroot-resolv.conf` (source: `postfix/files/fix-chroot-resolv.conf`) appends a second `ExecStartPre` — a short inline python program that writes `/var/spool/postfix/etc/resolv.conf` from a fixed list: `173.230.145.5` (Linode recursive, closest, and DNSBL-queryable unlike the public resolvers), `1.1.1.1`, `8.8.8.8`, plus `options timeout:2 attempts:2`. glibc honors only the first three `nameserver` lines (MAXNS), so those three are the whole list, one per failure domain, and the order is load-bearing — a dead or wrong first entry costs the `timeout:2` on every lookup. The stock `ExecStartPre` (`/usr/lib/postfix/configure-instance.sh`) snapshots `/etc/resolv.conf` into the chroot once per start and never refreshes it; because `/etc/resolv.conf` is a symlink into `/run/systemd/resolve/` that resolved rewrites on every restart (and tailscaled restarts resolved whenever it reasserts MagicDNS), that snapshot is a race. It was lost on 2026-08-27: an openssl unattended-upgrade daemon-reexec'd systemd and restarted networkd, resolved (twice, 104ms apart) and postfix inside one second, and postfix captured a resolv.conf with no nameservers. glibc's fallback is `127.0.0.1:53`, which here is Knot — authoritative-only, `REFUSED` for everything else — which postfix reports as `Host not found, try again`, so every remote delivery deferred for 23 hours. `systemd` runs `ExecStartPre` lines in order and drop-ins append, so ours lands after the snapshot and before `ExecStart`. Changing the drop-in needs a postfix **restart**, not a reload, since `ExecStartPre` only runs on start — `postfix/setup.py` wires that as a separate op from the ordinary config reload. Note the package also ships `postfix-resolvconf.path` (watch `/etc/resolv.conf`, re-sync, reload) — deliberately left disabled, since it would have shortened that outage but not prevented it, and it keeps postfix's resolver coupled to resolved's restart timing. Finally, `postfix/` carries the outbound-mail dead-man's switch — `/usr/local/sbin/postfix-ping-healthchecks.py` and its `.service` + `.timer`, firing every 30 minutes — because the probe is an actual mail message and so belongs with the MTA it exercises; see "Dead-man's switches" below.
- `opendkim/` — host-specific (same gate). Manages `/etc/opendkim.conf` and the three text tables under `/etc/dkimkeys/` (`signing.table`, `key.table`, `trusted.hosts`). The `.private` keys stay out-of-band (live secrets). Wired into postfix as a milter via `local:opendkim/opendkim.sock` (a unix socket inside postfix's chroot).
- `postsrsd/` — host-specific (same gate). Manages `/etc/default/postsrsd` for the Sender Rewriting Scheme daemon. Wired into postfix via `{sender,recipient}_canonical_maps = tcp:127.0.0.1:{10001,10002}` so mail FORWARDED through this host (alias_maps / virtual_alias_maps re-injection) gets its envelope-from rewritten to an SRS-encoded `@eacs.io` address — preserves SPF alignment at the next hop without forging the original sender. `SRS_EXCLUDE_DOMAINS` lists every domain whose envelope-from should be left alone: our local mail-receiving domains (eacs.io, approximately.competent.services, blackletterlabs.com, seventeengames.com) PLUS `ofb.net`, because this host is ofb's outbound :25 relay (GCE blocks outbound :25 from ofb), and ofb.net's SPF already authorizes 104.200.25.248 directly. Other ofb-hosted domains (tattoobag.com, etc.) are NOT excluded — when those appear in envelope-from here, it's via ofb-side forwarding of probably-spoofed mail, which is exactly what SRS should rewrite. The HMAC secret at `/etc/postsrsd.secret` is package-generated on first install (mode 0600, owner=postsrs) and stays out of the repo. `postsrsd/` is included in `deploy.py` BEFORE `postfix/` so postsrsd is configured + running before postfix reload activates the canonical_maps lookup.
- `dns/` — host-specific (`Hostname == "egnor-2020"`). Knot DNS authoritative server. Primary for user-owned zones, with source-of-truth zone files at `/etc/knot/zones/` managed from this repo and Hurricane Electric (`ns{1..5}.he.net`) as the AXFR-pulling secondary, registered per-zone at `dns.he.net`. Replaces BIND9 — `dns/setup.py` stops and disables `named.service` so Knot can claim port 53. Also drops in `DNSStubListener=no` for systemd-resolved (and repoints `/etc/resolv.conf` at the non-stub `/run/systemd/resolve/resolv.conf` that resolved still maintains) so the stub on `127.0.0.53` doesn't conflict with Knot's `0.0.0.0:53` bind. Knot's mutable state (journals, slave-zone caches) stays at the package default `/var/lib/knot/`; primary-zone files in `knot.conf` use absolute paths into `/etc/knot/zones/`. Knot bumps SOA serials itself (`serial-policy: unixtime`, `zonefile-load: difference-no-serial`, `journal-content: all`) so primary zone files can keep `1` as the serial forever.
- `netdata/` — Netdata config. Parent vs child role picked by hostname (`egnor-2020` is the parent; everywhere else is a child streaming up to it). On Linux, manages `netdata.conf` + `stream.conf` (config dir `/etc/netdata`), plus the `go.d/` and `health.d/` overrides, and installs `smartmontools` so the go.d `smartctl` collector reports SMART disk health on physical hosts; alerts are evaluated on the parent (`files.parent/health.d/`) since children run with `[health] enabled = no`. Fleet-wide alerts beyond SMART: failed systemd service units (`health.d/systemdunits.conf` — netdata ships this template disabled via a match-nothing `unit_name=!*` selector; our same-named file replaces the stock one and enables it) and unattended-upgrades freshness (`go.d/filecheck.conf` on parent+children watches `/var/lib/apt/periodic/upgrade-stamp`, touched only on successful u-u runs; `health.d/apt_upgrade.conf` alerts on stale or never-created stamps — needed because `apt.systemd.daily` swallows u-u's exit code, so u-u failures never fail the systemd unit). External endpoints (our sites plus Shopify-hosted `shop.seventeengames.com`) are probed from the parent by `go.d/httpcheck.conf` — plain 200-OK jobs and redirect-assertion jobs (`not_follow_redirects` + `status_accepted` + `header_match` on `Location`, so a changed redirect target alerts until the config is updated to match) — with cert expiry covered separately by `go.d/x509check.conf`, one job per (host, port). This replaces what used to be a handful of uptimerobot monitors emailing on failure. The parent also carries the netdata dead-man's switch — `/usr/local/sbin/netdata-ping-healthchecks.py` and its `.service` + `.timer`, firing every 5 minutes — which is the one alert that must originate outside this host, since netdata cannot report its own death; see "Dead-man's switches" below.
- `user/` — per-user dotfiles, gated on `Os == "Linux"` (skips BSD, OS X, and other non-Linux). `setup.py` symlinks every leaf under `user/files-linux/` into the target's `$HOME`, plus `user/files-linux-modern/` on Ubuntu 20.04+ (tools whose prebuilt binaries need a recent glibc — mise conf.d, the LazyVim nvim config). `user/copy-files/` holds the few files that must be copied not linked (e.g. `.forward`). A "leaf" is a regular file, a symlink, or a directory containing `.git` (the latter two are linked as a unit, not recursed into). Probes `~/source/dotfiles` and `~/dotfiles` for an existing checkout (and clones to `~/dotfiles` otherwise).
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

## Adding an endpoint to HTTP monitoring

All external endpoint checks run from the parent (egnor-2020) and are configured in `netdata/files.parent/go.d/`:

1. Add a job to `go.d/httpcheck.conf`. Plain availability is two lines (`name:` + `url:`); to assert a redirect instead, copy the `not_follow_redirects` + `status_accepted` + `header_match` shape from a neighboring job. Watch the status code — nginx `rewrite ... redirect` emits **302**, `rewrite ... permanent` and `return 301` emit **301**.
2. If the hostname is new, add it to `go.d/x509check.conf` (`https://<host>:443`) so cert expiry is covered too. One job per (host, port) — paths don't matter, the cert is the same.
3. `pyinfra eacs.io deploy.py`. Netdata restarts and picks up both.
4. Verify the job is collecting: `sudo netdatacli dumpconfig 2>/dev/null | grep -i <name>`, or just watch for the new chart under `httpcheck.status` on the dashboard.

Stock alert templates in `/usr/lib/netdata/conf.d/health.d/httpcheck.conf` cover bad status, bad header, no connection, and timeouts, so a new job needs no health config. `health.d/httpcheck.conf` exists only to split one chronically flappy endpoint (`shop.seventeengames.com`, which is Shopify's uptime, not ours) onto a longer-window template — add to that split only if a new endpoint turns out to be similarly noisy.

## Alert deep links and the netdata registry

The "View node" action on ntfy notifications does NOT use `${goto_url}` from `alarm-notify.sh`, and deliberately so. That variable points at `registry.my-netdata.io/registry-alert-redirect.html` (built at `alarm-notify.sh:2643`, with `NETDATA_REGISTRY_URL` defaulting to the public registry at line 290, since we run no registry of our own — `[registry] enabled = no`).

The registry resolves a machine GUID to an agent URL **per browser**: it only knows URLs at which that specific browser previously loaded that agent's dashboard, keyed by a person GUID in a registry cookie. That design targets agents on private LANs, where no single URL is globally valid. Ours is the opposite case — one agent, one permanent public URL — and notifications are usually opened on a phone that has never loaded the dashboard, so the registry has no mapping and serves "Can't find any Netdata Agent for this alert" every time.

So `custom_sender()` builds the link itself from `NETDATA_DASHBOARD_URL`, using the same shape `registry-alert-redirect.html` would have produced once it resolved an agent URL (its line 101):

```
${NETDATA_DASHBOARD_URL}/spaces/${host}/rooms/local/alerts/${transition_id}?${redirect_params}
```

`transition_id` and `redirect_params` are globals set by `alarm-notify.sh` before senders run. The agent serves its SPA for that path (verified: HTTP 200, same index as `/`), so routing happens client-side. The link is behind the dashboard's nginx basic auth (`nginx/files/sites-enabled/netdata`), same as any dashboard URL. If the dashboard ever moves off `netdata.eacs.io`, update `NETDATA_DASHBOARD_URL` at the top of `health_alarm_notify.conf`.

Note the `${host}` in the path is the *alerting* host, which for a child-node alert is the child, not the parent. That case is unverified — click-test a child alert before relying on it.

## Dead-man's switches (healthchecks.io)

Two probes that report to an *external* service, for the failures nothing in this
repo can report itself. Everything else here alerts *from* egnor-2020, so
egnor-2020's own death is the one outage it cannot announce: netdata, the alert
evaluator, postfix, and several of the monitored sites all go at once.

Each probe is a small python script run by a `oneshot` service on a timer. Both
report to healthchecks.io, which notifies the same `ntfy.sh/eacs-alerts` topic
netdata uses, so everything still lands in one place.

| | netdata switch | outbound-mail switch |
| --- | --- | --- |
| source | `netdata/files.parent/netdata-ping-healthchecks.{py,service,timer}` | `postfix/files/postfix-ping-healthchecks.{py,service,timer}` |
| deployed by | `netdata/setup.py` (parent gate) | `postfix/setup.py` |
| period | every 5 min (`OnCalendar=*:0/5`) | every 30 min (`OnCalendar=*:0/30`) |
| the probe | HTTP GET of the ping URL, but only after local netdata answers `http://127.0.0.1:19998/api/v1/info` | a mail message: `sendmail -f mail-deadman@eacs.io` to `<uuid>@hc-ping.com` |
| what it covers | host-down, netdata-dead, netdata-wedged | the whole outbound path: postfix, the chrooted resolver, DNS, outbound :25, and the queue actually moving |

The scripts install to `/usr/local/sbin/` and the units to
`/etc/systemd/system/`. Editing a script needs no `daemon-reload` (it is re-read
on every firing); editing a `.service` or `.timer` does, and `setup.py` handles
that. Both scripts exit non-zero on failure, so a broken probe trips netdata's
own `systemdunits` alert rather than going quietly dark.

The netdata switch pings `<url>/fail` when netdata does not answer, which alerts
immediately instead of waiting out the grace period, then re-raises so the unit
fails too.

**The ping URL and mail address are in the scripts, in the repo, deliberately.**
They are forgeable-ping secrets: holding one lets someone keep this one alert
quiet, and nothing else. The mail address already lands in `/var/log/mail.log`
as the recipient of every probe (plus its rotated archives) regardless. Keeping
them inline buys self-contained scripts with no `/etc/default` sourcing step and
no way to deploy a switch that was never configured.

### One-time setup at healthchecks.io

`pyinfra` deploys the timers but cannot create the account or the checks.

1. Create a check named `eacs.io netdata`, **period 5m**, **grace 10m**.
   healthchecks.io marks a check late at `period` and down at `period + grace`,
   so that alerts ~15 min after the last good ping: long enough to ride out a
   clean reboot (the timer is `Persistent=true`, so a reboot pings as soon as it
   is up), short enough that a reboot which *doesn't* come back is caught fast.
   Brief "late" blips between pings are normal and don't notify.
2. Create a second check named `eacs.io mail`, **period 1h**, **grace 1h**.
   Slower on purpose: mail is bursty, and a greylist or a ten-minute Google
   hiccup should not page anyone. Worst case is ~2h to alert, still two orders of
   magnitude better than the 23 hours the 2026-08-27 outage took to notice.
3. In the project's **Integrations**, add **ntfy**: topic `eacs-alerts`, server
   `https://ntfy.sh`, an access token with publish rights on that topic, priority
   **max** for down and **default** for up. Attach it to *both* checks. Max (not
   high) because this is the alert that arrives when nothing else can, and on
   ntfy max bypasses Do Not Disturb — affordable here because reboots on this
   host are deliberate, not automatic (`tweaks/files/apt-auto-upgrades` sets no
   `Unattended-Upgrade::Automatic-Reboot`), so false alarms are rare. Generate a
   fresh token rather than reusing `NTFY_ACCESS_TOKEN` from
   `/etc/netdata/health_alarm_notify_secrets.conf` — same topic, separately
   revocable.
4. Copy each check's ping URL / email ping address into the corresponding script
   and deploy: `pyinfra eacs.io deploy.py`.
5. Force one firing of each and confirm both checks go green:

   ```
   sudo systemctl start netdata-ping-healthchecks.service
   sudo systemctl start postfix-ping-healthchecks.service
   journalctl -u postfix-ping-healthchecks.service -n 20
   sudo grep hc-ping /var/log/mail.log | tail -3      # want status=sent
   systemctl list-timers '*-ping-healthchecks.timer'
   ```

6. Test the alert path end to end by pausing a check at healthchecks.io (or
   stopping its timer and waiting out the grace period) and confirming the ntfy
   notification arrives.

`hc-ping.com` publishes no MX record, so mail to it falls back to its A records
per RFC 5321 §5.1; postfix does that natively and needs no special config.

### Things not to change without reading this first

`sendmail` injects into the maildrop queue and returns success even when postfix
is stopped, so a green `postfix-ping-healthchecks.service` does **not** mean the
mail was delivered — only arrival registers the ping. That is exactly the
property that makes this a dead-man's switch rather than a liveness check.

Do not fold the two checks into one. The pair is diagnostic: both silent means
the host is gone, mail alone means the host is fine and delivery specifically is
broken. Nor is this a job for a queue-depth alert — this host carries a permanent
backlog of undeliverable spam and backscatter that ages out on its own, so depth
and even deferral count are uninformative, and any threshold picked today is
wrong next month.

A down/up pair from healthchecks.io arrives as **two separate ntfy
notifications**, unlike netdata's own alerts, which collapse warning → critical →
clear into one updating card via `X-Sequence-ID` (see `custom_sender()` in
`health_alarm_notify.conf`). That difference is deliberate. healthchecks.io's
ntfy integration has no custom-header hook — its form is only topic / server /
token / two priorities — so matching netdata's behavior would mean replacing it
with the generic Webhook integration, which *does* allow arbitrary headers and
separate down/up request configs. We don't, because: an incident here produces
exactly two events rather than a noisy oscillation, a persistent red card is
desirable for the alert of last resort (an outage that self-resolves overnight
should still be visible in the morning), and hand-rolling the webhook body loses
healthchecks' own formatting — downtime duration, ping counts, the tap-through
link — in the one notification most likely to be read half-awake. It would also
move live config into the healthchecks.io web UI, outside this repo.

Note the deliberate asymmetry: netdata alerts are *evaluated* on egnor-2020 and
go silent with it, so healthchecks.io is the only alert source that survives the
host being down. It has exactly one job — keep it that way, and don't move
netdata alerts into it.

## Adding a new area

1. Create `<area>/setup.py` and `<area>/files/`. (`netdata/` is the one exception: it splits into `files.parent/` and `files.child/`, selected by role.)
2. Gate the work on whatever fact applies (`Hostname`, `LinuxName`, group membership) so other hosts no-op cleanly.
3. Reference content with `src="<area>/files/<name>"` (resolved from the deploy directory, which is the repo root when running `pyinfra ... deploy.py`).
4. Files that should look identical in repo and on disk get a header in the source file itself — no template needed. The header names the file's path in this repo, `dotfiles/`-prefixed, in whatever comment syntax the file uses: `# Managed by pyinfra. Source: dotfiles/<area>/files/<name>`. Use `files.template` (Jinja) only if you need real interpolation.
5. Name each op after what it produces on the target, not after the area: the destination path for a `files.put` (`/etc/postfix/main.cf`), the unit name for a `systemd.service` (`postfix reload for config change`). The area is already in the left column of pyinfra's output, so an `area: ` prefix just repeats it.
6. Wire follow-up actions (reload/restart) with `_if=op.did_change` (one op) or `_if=any_changed(op1, op2, ...)` (multiple). Note `any_changed(*ops)` takes ops as separate arguments — passing a list raises `AttributeError` at deploy time, and only on a real run, since `--dry` never evaluates `_if`.
7. Add `local.include("<area>/setup.py")` to `deploy.py`, alphabetically.

## Retiring a unit, a script, or an area

`pyinfra` only converges what the deploy still declares — it never removes files
that used to be declared. Deleting an area from `deploy.py` leaves everything it
ever installed on every host it ever ran against.

So after removing or renaming a systemd unit, on each affected host:

```
sudo systemctl disable --now <old>.timer <old>.service
sudo systemctl reset-failed <old>.service <old>.timer
#   wait one collector cycle for the CLEAR notification, then:
sudo rm /etc/systemd/system/<old>.{service,timer} /usr/local/sbin/<old>
sudo systemctl daemon-reload
```

`reset-failed` **before** the `rm`, not after, and that ordering is the whole
point. A unit whose file disappears before the `daemon-reload` lands in
`not-found`/`failed` and *stays* there, tripping netdata's `systemdunits` alert
until cleared — deleting the file is not enough. But there is a second reason:
netdata raises that alert per unit, and when the unit file vanishes the alert's
chart instance is obsoleted, so the alert goes to `REMOVED` rather than `CLEAR`.
`alarm-notify.sh` drops anything that is not WARNING/CRITICAL/CLEAR before any
sender runs (its line 359), earlier than the `clear_alarm_always` check, so a
deleted failed unit produces a raise with no matching clear — and the ntfy card
stays red forever, since the `X-Sequence-ID` collapse needs a follow-up
notification to update it. Clearing the failed state while the unit still exists
gives a real WARNING → CLEAR transition first; the later removal is then silent
because nothing is active.

## Gating idioms

- OS family: `if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):`
- Specific host: `if host.get_fact(Hostname) == "egnor-2020":`
- Group membership: `if "system_admin" in host.groups:`

We deliberately don't maintain a central host-config dict; each area's `setup.py` checks for the hosts it should run on.

## Tooling expectations

`user/files-linux/.config/mise/config.toml` pins the tools the `.zshrc` expects to find on PATH — currently `uv`, `gh`, `lazygit`, `ripgrep`, `zellij`, and `python` — with `user/files-linux-modern/.config/mise/conf.d/modern.toml` adding the ones whose prebuilt binaries need a recent glibc (`neovim`, `node`, `tree-sitter`, `@github/copilot-language-server`). Most are pinned to the `github:` backend rather than the default aqua one. `mise` is activated from `.zshrc` if present. If you add a shell helper that depends on a new binary, add it to the mise config in the same change.

The repo-root `mise.toml` and `pyproject.toml`/`uv.lock` set up the Python env that runs pyinfra itself (via `uv sync`). `pyproject.toml` also sets `[tool.ruff] line-length = 80`, which is there for editor-side formatting — ruff itself is not a declared dependency and nothing in CI enforces it.

Neovim config under `user/files-linux-modern/.config/nvim/` is a LazyVim starter — plugins are managed by lazy.nvim at runtime, not vendored here.
