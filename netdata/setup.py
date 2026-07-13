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

    # smartmontools provides `smartctl`, which the go.d smartctl collector
    # (go.d/smartctl.conf) shells out to via the setuid ndsudo helper for
    # SMART disk-health metrics + alerts. Physical hosts get real data;
    # virtualized hosts (e.g. the GCE parent) expose no SMART devices and
    # the collector idles. Restarting netdata after a first-time install is
    # what makes the collector notice smartctl, so it's wired into the
    # restart trigger below.
    smart_pkg = None
    if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
        smart_pkg = apt.packages(
            name="smartmontools (smartctl for the netdata SMART collector)",
            packages=["smartmontools"],
            _sudo=True,
        )

    config_updates = [
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

    # health_alarm_notify.conf is re-sourced by alarm-notify.sh on every
    # event (alarm-notify.sh.in:519), so changes take effect without a
    # netdata restart — kept out of the restart trigger below. Parent only:
    # the parent host is where alarms are evaluated.
    if role == "parent":
        files.put(
            name="health_alarm_notify.conf (parent)",
            src="netdata/files.parent/health_alarm_notify.conf",
            dest="/etc/netdata/health_alarm_notify.conf",
            mode="644",
            _sudo=True,
        )

    # create this directory to quiet some journal-spam
    files.directory(
        name="scripts.d/ directory",
        path="/etc/netdata/scripts.d",
        mode="755",
        _sudo=True,
    )

    # netdata.conf / stream.conf changes need a real restart; health.d/
    # changes alone could use `netdatacli reload-health`, but bundling
    # them into the restart trigger is simpler and still cheap.
    restart_triggers = list(config_updates)
    if smart_pkg is not None:
        restart_triggers.append(smart_pkg)

    systemd.service(
        name="Restart netdata if config changed",
        service="netdata.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(*restart_triggers),
    )
