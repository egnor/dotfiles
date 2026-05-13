# Knot DNS authoritative server for egnor-2020. Plays two roles:
#   1) Primary for user-owned zones — source-of-truth zone files at
#      /etc/knot/zones/ managed by this script. Hurricane Electric is the
#      AXFR-pulling secondary, registered per-zone at dns.he.net.
#   2) Secondary (ns2.ofb.net) for ofb.net's 124 zones, slaved from
#      104.197.242.163 (ns1.ofb.net). Same role BIND9 previously filled here.
#
# This script also stops + disables named.service so BIND9 frees port 53
# for Knot. Ordering is deliberate: write config files first, validate via
# `knotc conf-check`, only THEN stop BIND. A bad config aborts the deploy
# before BIND is taken down. See CLAUDE.md "BIND9 -> Knot first-time
# cutover" for the manual verification steps after first deploy.
#
# Storage split: zone files (read-only, managed from this repo) live at
# /etc/knot/zones/; Knot's mutable state (journals, slave-zone caches)
# stays at the package default /var/lib/knot/. Each primary zone in
# knot.conf uses an absolute `file:` path into /etc/knot/zones/.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import apt, files, server, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    apt.packages(
        name="knot package",
        packages=["knot"],
        _sudo=True,
    )

    # systemd-resolved by default runs a stub listener on 127.0.0.53:53 (and
    # 127.0.0.54:53), which falls inside the 0.0.0.0:53 wildcard Knot wants
    # to bind. Disable the stub via drop-in, repoint /etc/resolv.conf at the
    # non-stub resolv.conf resolved already maintains, restart resolved so
    # it releases the sockets. The host keeps a working resolver (the
    # non-stub file lists Linode's upstreams that resolved tracks via DHCP).
    resolved_dropin = files.put(
        name="resolved: DNSStubListener=no drop-in",
        src="dns/files/resolved-no-stub.conf",
        dest="/etc/systemd/resolved.conf.d/no-stub.conf",
        mode="644",
        _sudo=True,
    )

    resolvconf_link = files.link(
        name="/etc/resolv.conf -> non-stub resolved file",
        path="/etc/resolv.conf",
        target="/run/systemd/resolve/resolv.conf",
        present=True,
        force=True,  # overwrite the existing symlink to stub-resolv.conf
        _sudo=True,
    )

    systemd.service(
        name="resolved: restart to drop stub listener",
        service="systemd-resolved.service",
        restarted=True,
        _sudo=True,
        _if=resolved_dropin.did_change,
    )

    # Side effect of dropping the stub: systemd-resolved's stub used to
    # synthesize the local hostname as a fake A record so `gethostbyname()`
    # could resolve it. Linode's upstream resolvers (now in resolv.conf)
    # don't know about it, so sudo/cron/etc. start complaining. Add a
    # /etc/hosts entry so the hostname resolves from /etc/nsswitch's `files`
    # source instead.
    files.line(
        name="/etc/hosts: 127.0.1.1 egnor-2020",
        path="/etc/hosts",
        line=r"^127\.0\.1\.1\s+egnor-2020(\s|$)",
        replace="127.0.1.1\tegnor-2020.ofb.net\tegnor-2020",
        _sudo=True,
    )

    config_updates = [
        files.put(
            name="knot.conf",
            src="dns/files/knot.conf",
            dest="/etc/knot/knot.conf",
            user="root",
            group="knot",
            mode="640",
            _sudo=True,
        ),
        files.sync(
            name="zones/",
            src="dns/files/zones",
            dest="/etc/knot/zones",
            user="root",
            group="knot",
            mode="644",
            dir_mode="755",
            delete=True,  # remove zone files not in repo
            _sudo=True,
        ),
    ]

    # Validate the freshly-written config before doing anything destructive.
    # Aborts the deploy if knotc rejects the config, leaving BIND still in
    # place. Re-runs on every deploy (cheap) so manual edits get caught too.
    server.shell(
        name="knot: conf-check before BIND stop",
        commands=["knotc -c /etc/knot/knot.conf conf-check"],
        _sudo=True,
    )

    # Only now do we stop BIND. If the config check above failed, we never
    # reach this line and BIND keeps owning port 53.
    bind_off = systemd.service(
        name="bind9: stop + disable (Knot takes over port 53)",
        service="named.service",
        running=False,
        enabled=False,
        _sudo=True,
    )

    systemd.service(
        name="knot: enable + ensure running",
        service="knot.service",
        running=True,
        enabled=True,
        _sudo=True,
    )

    # Restart (not reload) so Knot re-attempts the :53 socket bind, in case
    # it had previously failed to grab the port while BIND held it.
    systemd.service(
        name="knot: restart on config change / BIND stop / resolved drop-in",
        service="knot.service",
        restarted=True,
        _sudo=True,
        # Restart on any prior change that would let Knot grab :53 sockets it
        # couldn't grab before: stub listener removed, BIND stopped, or its
        # own config rewritten. Idempotent: no change above => no restart.
        _if=any_changed(resolved_dropin, bind_off, *config_updates),
    )
