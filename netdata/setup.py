# Netdata config. egnor-2020 is the parent (long-retention store, receives
# from children, evaluates all alerts); every other host is a child that
# streams metrics up. claim.conf (Cloud token) and the netdata package
# itself are managed out-of-band — this only manages the config files we
# actually customize. Skips hosts where netdata isn't installed.

from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Hostname, LinuxName, Os
from pyinfra.operations import apt, files, server, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Directory, "/etc/netdata"):
    role = "parent" if host.get_fact(Hostname) == "egnor-2020" else "child"

    # Add smartctl to enable SMART monitoring where available.
    smart_pkg = None
    if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
        smart_pkg = apt.packages(
            name="smartmontools (smartctl for the netdata SMART collector)",
            packages=["smartmontools"],
            _sudo=True,
        )

    # Everything a netdata restart is required to pick up.
    restart_triggers = [
        files.put(
            name=f"netdata.conf ({role})",
            src=f"netdata/files.{role}/netdata.conf",
            dest="/etc/netdata/netdata.conf",
            mode="644",
            _sudo=True,
        ),
        files.put(
            name=f"stream.conf ({role})",
            src=f"netdata/files.{role}/stream.conf",
            dest="/etc/netdata/stream.conf",
            mode="644",
            _sudo=True,
        ),
        files.sync(
            name=f"health.d/ overrides ({role})",
            src=f"netdata/files.{role}/health.d",
            dest="/etc/netdata/health.d",
            mode="644",
            dir_mode="755",
            _sudo=True,
        ),
        files.sync(
            name=f"go.d/ overrides ({role})",
            src=f"netdata/files.{role}/go.d",
            dest="/etc/netdata/go.d",
            mode="644",
            dir_mode="755",
            _sudo=True,
        ),
    ]

    if smart_pkg is not None:
        restart_triggers.append(smart_pkg)

    # Parent only: the parent host is where alarms are evaluated.
    if role == "parent":
        # Not a restart trigger — alarm-notify.sh re-sources this on every
        # event (its line 519), so edits apply immediately.
        files.put(
            name="health_alarm_notify.conf (parent)",
            src="netdata/files.parent/health_alarm_notify.conf",
            dest="/etc/netdata/health_alarm_notify.conf",
            mode="644",
            _sudo=True,
        )

        # Hack to set $clear_alarm_always which isn't picked up from configs.
        notify_env = files.put(
            name="netdata.service alarm-notify environment (parent)",
            src="netdata/files.parent/netdata-alarm-notify-env.conf",
            dest="/etc/systemd/system/netdata.service.d/alarm-notify-env.conf",
            mode="644",
            create_remote_dir=True,
            _sudo=True,
        )

        systemd.daemon_reload(
            _sudo=True,
            _if=notify_env.did_change,
        )

        restart_triggers.append(notify_env)

    # create this directory to quiet some journal-spam
    files.directory(
        name="scripts.d/ directory",
        path="/etc/netdata/scripts.d",
        mode="755",
        _sudo=True,
    )

    # use a simple restart; things like `reload-health` don't buy much.
    systemd.service(
        name="Restart netdata if config changed",
        service="netdata.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(*restart_triggers),
    )
