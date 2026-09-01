# Mosquitto MQTT broker for egnor-2020.
#
# /etc/mosquitto/mosquitto.conf is untouched, we add drop-ins.
# /etc/mosquitto/conf.d/egnor_mqtt.passwd is hand-managed, NOT in this repo.

from pyinfra import host
from pyinfra.facts.files import Sha256File
from pyinfra.facts.server import Hostname
from pyinfra.operations import apt, files, server, systemd
from pyinfra.operations.util import any_changed

CERTS_DIR = "/etc/mosquitto/certs"
CERTS_ORIGIN_DIR = "/etc/letsencrypt/live/competent.services"
CERT_HOOK = "/etc/letsencrypt/renewal-hooks/deploy/mosquitto-install-certs"

if host.get_fact(Hostname) == "egnor-2020":
    # mosquitto-clients included to facilitate testing
    apt_update = apt.packages(
        name="mosquitto + mosquitto-clients packages",
        packages=["mosquitto", "mosquitto-clients"],
        _sudo=True,
    )

    # egnor_mqtt.passwd permissions (future mosquitto will require this)
    files.file(
        name="/etc/mosquitto/conf.d/egnor_mqtt.passwd ownership",
        path="/etc/mosquitto/conf.d/egnor_mqtt.passwd",
        user="mosquitto",
        group="mosquitto",
        mode="600",
        _sudo=True,
    )

    config_update = files.put(
        name="/etc/mosquitto/conf.d/egnor_mqtt.conf",
        src="mosquitto/files/egnor_mqtt.conf",
        dest="/etc/mosquitto/conf.d/egnor_mqtt.conf",
        mode="644",
        _sudo=True,
    )

    files.directory(
        name=f"{CERTS_DIR} directory",
        path=CERTS_DIR,
        mode="755",
        _sudo=True,
    )

    files.put(
        name=CERT_HOOK,
        src="mosquitto/files/mosquitto-install-certs",
        dest=CERT_HOOK,
        mode="755",
        _sudo=True,
    )

    # sync from certbot to mosquitto (hook handles updated after that)
    def sha(f):
        return host.get_fact(Sha256File, path=f, _sudo=True)

    if any(
        sha(f"{CERTS_ORIGIN_DIR}/{f}") != sha(f"{CERTS_DIR}/{f}")
        for f in ("fullchain.pem", "privkey.pem")
    ):
        server.shell(name=f"{CERTS_DIR} sync", commands=[CERT_HOOK], _sudo=True)

    systemd.service(
        name="mosquitto.service enable",
        service="mosquitto.service",
        running=True,
        enabled=True,
        _sudo=True,
    )

    # `listener` changes require restart (not reload) to pick up
    systemd.service(
        name="mosquitto restart for config change",
        service="mosquitto.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(apt_update, config_update),
    )
