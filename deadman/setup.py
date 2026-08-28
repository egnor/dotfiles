# Dead-man's switches for egnor-2020 -- two timers that tickle external
# healthchecks.io checks, so the things that cannot report their own death
# get reported by something off-box.
#
#   netdata-deadman  HTTP ping, gated on local netdata answering. Covers
#                    host-down, netdata-dead and netdata-wedged.
#   mail-deadman     the ping *is* a mail message, so it covers the whole
#                    outbound path: postfix, the chrooted resolver, DNS,
#                    outbound :25, and the queue actually moving.
#
# Separate checks on purpose: both silent means the host is gone, mail alone
# means the host is fine and delivery is broken.
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

    # Second dead-man's switch, same shape, different failure domain: the
    # probe is a mail message to a healthchecks.io email-ping address, so
    # registering the ping requires the whole outbound path to work. Kept as
    # a separate check from netdata-deadman so the pair is diagnostic --
    # both down means the host is gone, this one alone means the mail path
    # is broken. Needs /etc/default/mail-deadman out-of-band; see CLAUDE.md.
    files.put(
        name="mail-deadman script",
        src="deadman/files/mail-deadman",
        dest="/usr/local/sbin/mail-deadman",
        mode="755",
        _sudo=True,
    )

    mail_service_unit = files.put(
        name="mail-deadman.service",
        src="deadman/files/mail-deadman.service",
        dest="/etc/systemd/system/mail-deadman.service",
        mode="644",
        _sudo=True,
    )

    mail_timer_unit = files.put(
        name="mail-deadman.timer",
        src="deadman/files/mail-deadman.timer",
        dest="/etc/systemd/system/mail-deadman.timer",
        mode="644",
        _sudo=True,
    )

    systemd.daemon_reload(
        _sudo=True,
        _if=any_changed(mail_service_unit, mail_timer_unit),
    )

    systemd.service(
        name="Enable mail-deadman.timer",
        service="mail-deadman.timer",
        running=True,
        enabled=True,
        _sudo=True,
    )

    systemd.service(
        name="Restart mail-deadman.timer if the unit changed",
        service="mail-deadman.timer",
        restarted=True,
        _sudo=True,
        _if=mail_timer_unit.did_change,
    )
