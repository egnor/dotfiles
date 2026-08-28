# Netdata config. egnor-2020 is the parent (long-retention store, receives
# from children, evaluates all alerts); every other host is a child that
# streams metrics up. claim.conf (Cloud token) and the netdata package
# itself are managed out-of-band — this only manages the config files we
# actually customize. Skips hosts where netdata isn't installed.

from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Hostname, LinuxName
from pyinfra.operations import apt, files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Directory, "/etc/netdata"):
    role = "parent" if host.get_fact(Hostname) == "egnor-2020" else "child"

    netdata_restart_triggers = [
        files.put(
            name=f"/etc/netdata/netdata.conf ({role})",
            src=f"netdata/files.{role}/netdata.conf",
            dest="/etc/netdata/netdata.conf",
            mode="644",
            _sudo=True,
        ),
        files.put(
            name=f"/etc/netdata/stream.conf ({role})",
            src=f"netdata/files.{role}/stream.conf",
            dest="/etc/netdata/stream.conf",
            mode="644",
            _sudo=True,
        ),
        files.sync(
            name=f"/etc/netdata/health.d/ overrides ({role})",
            src=f"netdata/files.{role}/health.d",
            dest="/etc/netdata/health.d",
            mode="644",
            dir_mode="755",
            _sudo=True,
        ),
        files.sync(
            name=f"/etc/netdata/go.d/ overrides ({role})",
            src=f"netdata/files.{role}/go.d",
            dest="/etc/netdata/go.d",
            mode="644",
            dir_mode="755",
            _sudo=True,
        ),
    ]

    # Add smartctl to enable SMART monitoring where available.
    if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
        smartmontools_update = apt.packages(
            name="smartmontools package for netdata",
            packages=["smartmontools"],
            _sudo=True,
        )
        netdata_restart_triggers.append(smartmontools_update)

    # Parent only: the parent host is where alarms are evaluated.
    if role == "parent":
        systemd_triggers = []

        # re-sourced on every alarm event by alarm-notify.sh
        files.put(
            name="/etc/netdata/health_alarm_notify.conf",
            src="netdata/files.parent/health_alarm_notify.conf",
            dest="/etc/netdata/health_alarm_notify.conf",
            mode="644",
            _sudo=True,
        )

        systemd_clear_update = files.put(
            name="netdata.service set $clear_alarm_always",
            src="netdata/files.parent/clear-alarm-always.conf",
            dest="/etc/systemd/system/netdata.service.d/clear-alarm-always.conf",
            mode="644",
            create_remote_dir=True,
            _sudo=True,
        )
        netdata_restart_triggers.append(systemd_clear_update)
        systemd_triggers.append(systemd_clear_update)

        files.put(
            name="/usr/local/sbin/netdata-ping-healthchecks.py",
            src="netdata/files.parent/netdata-ping-healthchecks.py",
            dest="/usr/local/sbin/netdata-ping-healthchecks.py",
            mode="755",
            _sudo=True,
        )

        ping_service_update = files.put(
            name="netdata-ping-healthchecks.service",
            src="netdata/files.parent/netdata-ping-healthchecks.service",
            dest="/etc/systemd/system/netdata-ping-healthchecks.service",
            mode="644",
            _sudo=True,
        )
        systemd_triggers.append(ping_service_update)

        ping_timer_update = files.put(
            name="netdata-ping-healthchecks.timer",
            src="netdata/files.parent/netdata-ping-healthchecks.timer",
            dest="/etc/systemd/system/netdata-ping-healthchecks.timer",
            mode="644",
            _sudo=True,
        )
        systemd_triggers.append(ping_timer_update)

        systemd.daemon_reload(_sudo=True, _if=any_changed(*systemd_triggers))

        systemd.service(
            name="netdata-ping-healthchecks.timer enable",
            service="netdata-ping-healthchecks.timer",
            running=True,
            enabled=True,
            _sudo=True,
        )

        systemd.service(
            name="netdata-ping-healthchecks.timer restart for unit change",
            service="netdata-ping-healthchecks.timer",
            restarted=True,
            _sudo=True,
            _if=any_changed(ping_timer_update),
        )

    # create this directory to quiet some journal-spam
    files.directory(
        name="/etc/netdata/scripts.d/ directory",
        path="/etc/netdata/scripts.d",
        mode="755",
        _sudo=True,
    )

    # use a blunt restart; things like `reload-health` don't buy much.
    systemd.service(
        name="netdata restart for config change",
        service="netdata.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(*netdata_restart_triggers),
    )
