# Root-owned system tweaks that egnor likes.
# Tweaks are gated on facts so this file is safe to run on any target — the
# inapplicable ones simply skip.

from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import files, systemd

# "Ubuntu", "Debian", "Fedora", ... or None on non-Linux
if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
    # Passwordless sudo for the sudo group, via a drop-in
    files.put(
        name="sudo: NOPASSWD for sudo group",
        src="tweaks/files/sudo-group-nopasswd",
        dest="/etc/sudoers.d/sudo-group-nopasswd",
        mode="440",  # sudo refuses files writable by group/other
        _sudo=True,
    )

    # packagekitd's apt backend has a long-standing leak ; cap RSS so the
    # cgroup OOM killer reaps it before it drags the box into swap.
    packagekit_update = files.put(
        name="packagekit: memory cap drop-in",
        src="tweaks/files/packagekit-memory-limit.conf",
        dest="/etc/systemd/system/packagekit.service.d/memory-limit.conf",
        mode="644",
        _sudo=True,
    )

    systemd.daemon_reload(
        _sudo=True,
        _if=packagekit_update.did_change,
    )

    systemd.service(
        name="packagekit: restart to pick up change",
        service="packagekit.service",
        restarted=True,
        _sudo=True,
        _if=packagekit_update.did_change,
    )
