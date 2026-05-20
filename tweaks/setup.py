# Root-owned system tweaks that egnor likes.
# Tweaks are gated on facts so this file is safe to run on any target — the
# inapplicable ones simply skip.

from pyinfra import host
from pyinfra.facts.files import File
from pyinfra.facts.server import LinuxName
from pyinfra.facts.systemd import SystemdEnabled
from pyinfra.operations import files, server, systemd

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
    if "packagekit.service" in host.get_fact(SystemdEnabled):
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

    # brltty ships udev rules that tag common USB serial adapters as braille
    # displays, so brltty-udev.service grabs /dev/ttyUSB* the moment one is
    # plugged in -- inconvenient when the same chips show up on embedded dev
    # boards. We can't just remove brltty (ubuntu-desktop-minimal Depends on
    # it), so override the rules file with an empty same-named file in /etc/.
    # To revert: rm /etc/udev/rules.d/85-brltty.rules && udevadm control --reload
    if host.get_fact(File, path="/usr/lib/udev/rules.d/85-brltty.rules"):
        brltty_override = files.put(
            name="brltty: empty udev rules override",
            src="tweaks/files/brltty-udev-override.rules",
            dest="/etc/udev/rules.d/85-brltty.rules",
            mode="644",
            _sudo=True,
        )

        server.shell(
            name="brltty: reload udev rules",
            commands=["udevadm control --reload"],
            _sudo=True,
            _if=brltty_override.did_change,
        )

if host.get_fact(LinuxName) == "Ubuntu":
    # Install firefox from packages.mozilla.org instead of the ubuntu-shipped
    # snap-wrapper deb. Four pieces are needed; the pin alone isn't enough,
    # because unattended-upgrades reads its OWN origin allowlist rather than
    # apt's priority pin:
    #   - the signing key under /etc/apt/keyrings/
    #   - the deb822 source under /etc/apt/sources.list.d/
    #   - a Pin-Priority: 1000 in /etc/apt/preferences.d/  (for `apt install`)
    #   - a snippet adding "packages.mozilla.org:mozilla" to
    #     Unattended-Upgrade::Allowed-Origins  (for security updates)
    # Switching an existing snap-firefox install over is a one-time manual
    # step (`snap remove firefox && apt install firefox`); not done here.
    files.put(
        name="mozilla: apt signing key",
        src="tweaks/files/mozilla-apt-keyring.asc",
        dest="/etc/apt/keyrings/packages.mozilla.org.asc",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="mozilla: apt source",
        src="tweaks/files/mozilla-apt-source.sources",
        dest="/etc/apt/sources.list.d/mozilla.sources",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="mozilla: apt pin priority",
        src="tweaks/files/mozilla-apt-pin",
        dest="/etc/apt/preferences.d/mozilla",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="mozilla: unattended-upgrades allowed-origins",
        src="tweaks/files/mozilla-unattended-upgrades.conf",
        dest="/etc/apt/apt.conf.d/51unattended-upgrades-mozilla",
        mode="644",
        _sudo=True,
    )

    # Remove any leftover blanket firefox block from unattended-upgrades --
    # the mozilla source IS where we want updates to come from now.
    files.file(
        name="mozilla: drop legacy firefox block",
        path="/etc/apt/apt.conf.d/52unattended-block-firefox",
        present=False,
        _sudo=True,
    )
