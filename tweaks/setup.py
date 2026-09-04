# Root-owned system tweaks that egnor likes.
# Tweaks are gated on facts so this file is safe to run on any target — the
# inapplicable ones simply skip.

from pyinfra import host
from pyinfra.facts.files import Directory, File
from pyinfra.facts.server import LinuxName
from pyinfra.facts.systemd import SystemdEnabled
from pyinfra.operations import files, server, systemd
from pyinfra.operations.util import any_changed

# "Ubuntu", "Debian", "Fedora", ... or None on non-Linux
if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):
    # Passwordless sudo for the sudo group, via a drop-in
    files.put(
        name="/etc/sudoers.d/sudo-group-nopasswd",
        src="tweaks/files/sudo-group-nopasswd",
        dest="/etc/sudoers.d/sudo-group-nopasswd",
        mode="440",  # sudo refuses files writable by group/other
        _sudo=True,
    )

    # Ensure unattended-upgrades is actually enabled, not just installed --
    # see the source file for the eacs.io cautionary tale. Freshness of the
    # resulting /var/lib/apt/periodic/upgrade-stamp is monitored by netdata
    # (netdata/files.*/go.d/filecheck.conf + health.d/apt_upgrade.conf).
    files.put(
        name="/etc/apt/apt.conf.d/20auto-upgrades",
        src="tweaks/files/apt-auto-upgrades",
        dest="/etc/apt/apt.conf.d/20auto-upgrades",
        mode="644",
        _sudo=True,
    )

    # packagekitd's apt backend has a long-standing leak; cap RSS so the
    # cgroup OOM killer reaps it before it drags the box into swap.
    if "packagekit.service" in host.get_fact(SystemdEnabled):
        packagekit_update = files.put(
            name="/etc/systemd/system/packagekit.service.d/memory-limit.conf",
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

    # udev rules for embedded development: serial ports and USB dev tools
    # (debug probes, bootloaders, protocol analyzers) usable without root on
    # every machine, so a widget that works on one desk works on the next.
    # Sources are named for what they do; targets keep the numeric prefixes
    # udev sorts on. udev-brltty-disable.rules is the odd one out -- an EMPTY file
    # whose only job is to shadow the same-named file in /usr/lib/, so it's
    # gated on that file existing; see its header for why we can't just
    # remove the package. Only affects devices plugged in after the reload:
    # re-plug (or `udevadm trigger`) anything already attached.
    if host.get_fact(Directory, path="/etc/udev/rules.d"):
        udev_rules = [
            ("udev-serial-rw.rules", "60-serial-rw.rules"),
            ("udev-odrive.rules", "91-odrive.rules"),
            ("udev-platformio.rules", "99-platformio-udev.rules"),
            ("udev-totalphase.rules", "99-totalphase.rules"),
        ]
        if host.get_fact(File, path="/usr/lib/udev/rules.d/85-brltty.rules"):
            udev_rules.append(("udev-brltty-disable.rules", "85-brltty.rules"))

        udev_updates = [
            files.put(
                name=f"/etc/udev/rules.d/{dest}",
                src=f"tweaks/files/{src}",
                dest=f"/etc/udev/rules.d/{dest}",
                user="root",
                group="root",
                mode="644",
                _sudo=True,
            )
            for src, dest in udev_rules
        ]

        # Retired: the pre-pyinfra serial rule (replaced by 60-serial-rw),
        # an Ultimate Hacking Keyboard, and a Brother scanner, neither owned
        # any more.
        udev_updates += [
            files.file(
                name=f"/etc/udev/rules.d/{old}",
                path=f"/etc/udev/rules.d/{old}",
                present=False,
                _sudo=True,
            )
            for old in (
                "50-serial.rules",
                "50-uhk60.rules",
                "60-brother-libsane-type1-inst.rules",
            )
        ]

        server.shell(
            name="udev: reload rules",
            commands=["udevadm control --reload"],
            _sudo=True,
            _if=any_changed(*udev_updates),
        )

    # The cloud-init -> cloud-init-base package split left two IDENTICAL
    # logrotate rules for /var/log/cloud-init*.log (one per package, both under
    # /etc/logrotate.d/). logrotate aborts its whole run on a duplicate glob, so
    # logrotate.service failed nightly and NOTHING got rotated. cloud-init-base
    # owns the live rule; we stub the redundant cloud-init copy. Gated on BOTH
    # files existing so older Ubuntu (no split, single working rule) is left
    # alone. See tweaks/files/logrotate-cloud-init-stub for the full rationale.
    # No reload needed -- logrotate.timer re-reads config on its next run.
    if host.get_fact(
        File, path="/etc/logrotate.d/cloud-init"
    ) and host.get_fact(File, path="/etc/logrotate.d/cloud-init-base"):
        files.put(
            name="/etc/logrotate.d/cloud-init",
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
    #     Origins-Pattern (NOT legacy Allowed-Origins, whose strict id:codename
    #     parser crashes on key=value entries and aborts every u-u run),
    #     matched by site= (NOT o=, which u-u resolves against the repo's bogus
    #     Release Origin field and so never matches -- that mismatch made u-u
    #     "never"-pin mozilla and fall back to reinstalling the snap on every
    #     run; see that file for the full story).
    # Switching an existing snap-firefox install over is a one-time manual
    # step (`snap remove firefox && apt install firefox`); not done here.
    files.put(
        name="/etc/apt/keyrings/packages.mozilla.org.asc",
        src="tweaks/files/mozilla-apt-keyring.asc",
        dest="/etc/apt/keyrings/packages.mozilla.org.asc",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="/etc/apt/sources.list.d/mozilla.sources",
        src="tweaks/files/mozilla-apt-source.sources",
        dest="/etc/apt/sources.list.d/mozilla.sources",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="/etc/apt/preferences.d/mozilla",
        src="tweaks/files/mozilla-apt-pin",
        dest="/etc/apt/preferences.d/mozilla",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="/etc/apt/apt.conf.d/51unattended-upgrades-mozilla",
        src="tweaks/files/mozilla-unattended-upgrades.conf",
        dest="/etc/apt/apt.conf.d/51unattended-upgrades-mozilla",
        mode="644",
        _sudo=True,
    )

    # Remove any leftover blanket firefox block from unattended-upgrades --
    # the mozilla source IS where we want updates to come from now.
    files.file(
        name="/etc/apt/apt.conf.d/52unattended-block-firefox",
        path="/etc/apt/apt.conf.d/52unattended-block-firefox",
        present=False,
        _sudo=True,
    )

    # Likewise drop the mozillateam-PPA allowlist entry from the pre-
    # packages.mozilla.org approach; that PPA is no longer a configured source.
    files.file(
        name="/etc/apt/apt.conf.d/51unattended-upgrades-firefox",
        path="/etc/apt/apt.conf.d/51unattended-upgrades-firefox",
        present=False,
        _sudo=True,
    )
