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

    # The cloud-init -> cloud-init-base package split left two IDENTICAL
    # logrotate rules for /var/log/cloud-init*.log (one per package, both under
    # /etc/logrotate.d/). logrotate aborts its whole run on a duplicate glob, so
    # logrotate.service failed nightly and NOTHING got rotated. cloud-init-base
    # owns the live rule; we stub the redundant cloud-init copy. Gated on BOTH
    # files existing so older Ubuntu (no split, single working rule) is left
    # alone. See tweaks/files/logrotate-cloud-init-stub for the full rationale.
    # No reload needed -- logrotate.timer re-reads config on its next run.
    if host.get_fact(File, path="/etc/logrotate.d/cloud-init") and host.get_fact(
        File, path="/etc/logrotate.d/cloud-init-base"
    ):
        files.put(
            name="logrotate: stub duplicate cloud-init rule",
            src="tweaks/files/logrotate-cloud-init-stub",
            dest="/etc/logrotate.d/cloud-init",
            mode="644",
            _sudo=True,
        )

if host.get_fact(LinuxName) == "Ubuntu":
    # Install firefox from packages.mozilla.org instead of the ubuntu-shipped
    # snap-wrapper deb. Several cooperating pieces are needed; an apt pin alone
    # is not enough, because unattended-upgrades reads its OWN origin allowlist
    # rather than apt's priority pin:
    #   - the signing key under /etc/apt/keyrings/
    #   - the deb822 source under /etc/apt/sources.list.d/
    #   - /etc/apt/preferences.d/mozilla, which does TWO things:
    #       * Pin-Priority 1000 on the mozilla origin (so `apt install` picks it
    #         and is allowed to downgrade off the higher-epoch snap stub), and
    #       * Pin-Priority -1 on Ubuntu-origin firefox, so the snap-transitional
    #         deb is simply uninstallable and can never be selected.
    #   - a snippet adding the mozilla origin to Unattended-Upgrade::
    #     Allowed-Origins, matched by site= (NOT the bare host:suite shorthand,
    #     which u-u resolves against the repo's bogus Release Origin field and
    #     so never matches -- that mismatch made u-u "never"-pin mozilla and
    #     fall back to reinstalling the snap on every run; see that file).
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
