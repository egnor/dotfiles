# Self-hosted UniFi OS Server for skully. This is Ubiquiti's containerized
# (Podman) self-hosting platform — the successor to the standalone "UniFi
# Network Application" apt package. It bundles UniFi Network plus the wider
# UniFi OS (unified console, official remote access via Site Manager, room
# for other apps like Protect/Access) and self-updates from its own UI.
#
# Unlike the old Network app, UniFi OS Server is NOT an apt repo: it's an
# ~800MB versioned installer binary downloaded from fw-download.ubnt.com and
# run once as root. After that it manages its own upgrades. So pyinfra owns
# only the declarative + idempotent parts — uninstall the old apt approach,
# install Podman, and stage + checksum-verify the pinned installer. The one
# interactive installer run is a documented one-time step (see CLAUDE.md
# "Self-hosted UniFi OS Server (skully)").

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import apt, files, systemd

# Pinned UniFi OS Server release. Bump these together when seeding a newer
# base version (day-to-day upgrades happen in-app, not here). URL + md5 come
# from Ubiquiti's Download/Releases page; md5 cross-checked against the
# community installer script.
UOS_VERSION = "5.0.6"
UOS_URL = (
    "https://fw-download.ubnt.com/data/unifi-os-server/"
    "1856-linux-x64-5.0.6-33f4990f-6c68-4e72-9d9c-477496c22450.6-x64"
)
UOS_MD5 = "610b385c834bad7c4db00c29e2b8a9f1"
UOS_DEST = f"/opt/unifi-os-server/unifi-os-server-{UOS_VERSION}-x64"

if host.get_fact(Hostname) == "skully":
    # --- Retire the standalone UniFi Network Application apt setup ---
    # UniFi OS Server bundles its own Network app + MongoDB, and Ubiquiti
    # says to close the Network Server before installing it. Purge the apt
    # packages and remove the third-party repos/keys we previously added.
    apt.packages(
        name="purge old unifi + mongodb-org-server packages",
        packages=["unifi", "mongodb-org-server"],
        present=False,
        purge=True,
        _sudo=True,
    )

    for path in (
        "/etc/apt/sources.list.d/unifi.sources",
        "/etc/apt/sources.list.d/mongodb.sources",
        "/etc/apt/keyrings/unifi-repo.asc",
        "/etc/apt/keyrings/mongodb-server-8.0.asc",
    ):
        files.file(
            name=f"remove {path}",
            path=path,
            present=False,
            _sudo=True,
        )

    # The mongod mask is a /dev/null symlink, so it needs files.link (not
    # files.file) to remove. daemon-reload afterward so systemd forgets it.
    mongod_unmask = files.link(
        name="remove mongod.service mask symlink",
        path="/etc/systemd/system/mongod.service",
        present=False,
        _sudo=True,
    )

    systemd.daemon_reload(
        _sudo=True,
        _if=mongod_unmask.did_change,
    )

    # --- UniFi OS Server prerequisites ---
    # Podman 4.3.1+ (Docker is unsupported) and slirp4netns for rootless
    # container networking. Ubuntu 26.04 ships new-enough versions.
    apt.packages(
        name="podman + slirp4netns",
        packages=["podman", "slirp4netns"],
        _sudo=True,
    )

    # --- Stage the installer ---
    # Download + checksum-verify the pinned installer; idempotent (pyinfra
    # skips the re-download once the md5 matches). Running it is a one-time
    # manual step — it's interactive and may offer to migrate an existing
    # Network Server. See CLAUDE.md. files.download doesn't create its parent
    # dir, so make it first.
    files.directory(
        name="/opt/unifi-os-server staging dir",
        path="/opt/unifi-os-server",
        mode="755",
        _sudo=True,
    )

    files.download(
        name=f"unifi-os-server {UOS_VERSION} installer",
        src=UOS_URL,
        dest=UOS_DEST,
        md5sum=UOS_MD5,
        mode="755",
        _sudo=True,
    )
