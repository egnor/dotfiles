# Netdata config. egnor-2020 is the parent (long-retention store, receives
# from children, evaluates all alerts); every other host is a child that
# streams metrics up. claim.conf (Cloud token) and the netdata package
# itself are managed out-of-band — this only manages the config files we
# actually customize. Skips hosts where netdata isn't installed.

from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Hostname
from pyinfra.operations import files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Directory, "/etc/netdata"):
    role = "parent" if host.get_fact(Hostname) == "egnor-2020" else "child"

    netdata_conf = files.put(
        name=f"netdata.conf ({role})",
        src=f"netdata/files/{role}/netdata.conf",
        dest="/etc/netdata/netdata.conf",
        mode="644",
        _sudo=True,
    )

    stream_conf = files.put(
        name=f"stream.conf ({role})",
        src=f"netdata/files/{role}/stream.conf",
        dest="/etc/netdata/stream.conf",
        mode="644",
        _sudo=True,
    )

    # Parent-only: alert template overrides under /etc/netdata/health.d/
    # (children have [health] enabled = no, so they don't read these).
    # Additive sync — leave room for one-off `edit-config` drops.
    health_d = None
    if role == "parent":
        health_d = files.sync(
            name="health.d/ overrides",
            src="netdata/files/parent/health.d",
            dest="/etc/netdata/health.d",
            mode="644",
            dir_mode="755",
            _sudo=True,
        )

    # netdata.conf / stream.conf changes need a real restart; health.d/
    # changes alone could use `netdatacli reload-health`, but bundling
    # them into the restart trigger is simpler and still cheap.
    triggers = [netdata_conf, stream_conf]
    if health_d is not None:
        triggers.append(health_d)
    systemd.service(
        name="Restart netdata if config changed",
        service="netdata.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(*triggers),
    )
