# Root-owned system tweaks that egnor likes.
# Tweaks are gated on facts so this file is safe to run on any target — the
# inapplicable ones simply skip.

from pyinfra import host
from pyinfra.facts.files import Directory, File
from pyinfra.facts.server import Hostname, LinuxName
from pyinfra.facts.systemd import SystemdEnabled
from pyinfra.operations import files, server, systemd

# To make firefox comes from .deb instead of snap:
# - the signing key in /etc/apt/keyrings/
# - the deb822 source in /etc/apt/sources.list.d/
# - the pin priority in /etc/apt/preferences.d/
# - the Unattended-Upgrade::Origins-Pattern snippet in /etc/apt/apt.conf.d

# "Ubuntu", "Debian", "Fedora", ... or None on non-Linux
if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
    # Retire old files.
    for retire in [
        "/etc/sudoers.d/sudo-group-nopasswd",
        "/etc/apt/apt.conf.d/20auto-upgrades",
        "/etc/apt/apt.conf.d/51unattended-upgrades-firefox",
        "/etc/apt/apt.conf.d/51unattended-upgrades-mozilla",
        "/etc/apt/apt.conf.d/52unattended-block-firefox",
        "/etc/apt/preferences.d/mozilla",
        "/etc/apt/sources.list.d/mozilla.sources",
        "/etc/ssh/sshd_config.d/brute-force.conf",
        "/etc/systemd/system/packagekit.service.d/memory-limit.conf",
        "/etc/udev/rules.d/60-serial-rw.rules",
        "/etc/udev/rules.d/85-brltty.rules",
        "/etc/udev/rules.d/91-odrive.rules",
        "/etc/udev/rules.d/99-platformio-udev.rules",
        "/etc/udev/rules.d/99-totalphase.rules",
    ]:
        files.file(name=retire, path=retire, present=False, _sudo=True)

    # sudo policy tweaks.
    if host.get_fact(Directory, path="/etc/sudoers.d"):
        files.sync(
            name="sudoers.d",
            src="tweaks/files/sudoers.d",
            dest="/etc/sudoers.d",
            mode="644",  # sudo refuses files writable by group/other
            dir_mode="755",
            delete=False,
            _sudo=True,
        )

    # apt policy tweaks.
    if host.get_fact(Directory, path="/etc/apt"):
        files.sync(
            name="apt",
            src="tweaks/files/apt",
            dest="/etc/apt",
            mode="644",
            dir_mode="755",
            delete=False,
            _sudo=True,
        )

    # packagekit service tweaks.
    if "packagekit.service" in host.get_fact(SystemdEnabled):
        packagekit_update = files.sync(
            name="packagekit.service.d",
            src="tweaks/files/packagekit.service.d",
            dest="/etc/systemd/system/packagekit.service.d",
            mode="644",
            dir_mode="755",
            delete=False,
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

    # udev rules.
    if host.get_fact(Directory, path="/etc/udev/rules.d"):
        udev_update = files.sync(
            name="udev/rules.d",
            src="tweaks/files/udev.rules.d",
            dest="/etc/udev/rules.d",
            mode="644",
            dir_mode="755",
            delete=False,
            _sudo=True,
        )

        server.shell(
            name="udev: reload rules",
            commands=["udevadm control --reload"],
            _sudo=True,
            _if=udev_update.did_change,
        )

    # sshd service tweaks.
    if host.get_fact(Hostname) == "egnor-2020":
        sshd_update = files.sync(
            name="sshd_config.d",
            src="tweaks/files/sshd_config.d",
            dest="/etc/ssh/sshd_config.d",
            mode="644",
            dir_mode="755",
            delete=False,
            _sudo=True,
        )

        # Validate before reloading. Fix immediately on failure!!
        server.shell(
            name="sshd -t (validate config)",
            commands=["sshd -t"],
            _sudo=True,
            _if=sshd_update.did_change,
        )

        # Reload, not restart (leaves existing connections intact).
        systemd.service(
            name="ssh reload for config change",
            service="ssh.service",
            reloaded=True,
            _sudo=True,
            _if=sshd_update.did_change,
        )

    # Clean up a wart from the cloud-init -> cloud-init-base package split.
    if all(
        host.get_fact(File, path=f"/etc/logrotate.d/{p}")
        for p in ("cloud-init", "cloud-init-base")
    ):
        files.put(
            name="logrotate.d/cloud-init",
            src="tweaks/files/logrotate.d/cloud-init",
            dest="/etc/logrotate.d/cloud-init",
            mode="644",
            _sudo=True,
        )
