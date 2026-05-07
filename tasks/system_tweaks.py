# Root-owned system tweaks. Replaces system_tweaks.py.
# Each tweak: write a file, then daemon-reload + restart only if it changed.

from pyinfra.operations import files, systemd

# packagekitd has a long-standing leak in its apt backend; cap RSS so the
# cgroup OOM killer reaps it before it drags the box into swap.
packagekit_drop_in = files.put(
    name="packagekit memory cap drop-in",
    src="files/packagekit-memory-limit.conf",
    dest="/etc/systemd/system/packagekit.service.d/memory-limit.conf",
    mode="644",
    create_remote_dir=True,
    _sudo=True,
)

systemd.daemon_reload(
    _sudo=True,
    _if=packagekit_drop_in.did_change,
)

systemd.service(
    name="Restart packagekit if its drop-in changed",
    service="packagekit.service",
    restarted=True,
    _sudo=True,
    _if=packagekit_drop_in.did_change,
)
