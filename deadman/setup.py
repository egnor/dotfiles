# Dead-man's switch for the netdata parent (egnor-2020 only).
#
# The rest of this repo alerts *from* egnor-2020, which means egnor-2020's
# own death is the one outage nothing here can report: the monitoring
# parent, the alert evaluator, the mail server, and several of the
# monitored sites all live on it. A timer pings an external
# healthchecks.io check every 5 minutes -- but only when local netdata
# answers its API -- and healthchecks.io alerts to the same ntfy topic
# when the pings stop. See CLAUDE.md for the one-time healthchecks.io
# setup and the out-of-band /etc/default/netdata-deadman.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    files.put(
        name="netdata-deadman script",
        src="deadman/files/netdata-deadman",
        dest="/usr/local/sbin/netdata-deadman",
        mode="755",
        _sudo=True,
    )

    service_unit = files.put(
        name="netdata-deadman.service",
        src="deadman/files/netdata-deadman.service",
        dest="/etc/systemd/system/netdata-deadman.service",
        mode="644",
        _sudo=True,
    )

    timer_unit = files.put(
        name="netdata-deadman.timer",
        src="deadman/files/netdata-deadman.timer",
        dest="/etc/systemd/system/netdata-deadman.timer",
        mode="644",
        _sudo=True,
    )

    systemd.daemon_reload(
        _sudo=True,
        _if=any_changed(service_unit, timer_unit),
    )

    # The timer is what gets enabled; the .service is oneshot and pulled in
    # by it. Unconditional (pyinfra no-ops when it is already active) so a
    # hand-stopped timer gets put back on the next deploy. The script is
    # re-read on every firing, so changes to it need no restart here.
    systemd.service(
        name="Enable netdata-deadman.timer",
        service="netdata-deadman.timer",
        running=True,
        enabled=True,
        _sudo=True,
    )

    systemd.service(
        name="Restart netdata-deadman.timer if the unit changed",
        service="netdata-deadman.timer",
        restarted=True,
        _sudo=True,
        _if=timer_unit.did_change,
    )
