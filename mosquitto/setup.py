# Mosquitto MQTT broker for egnor-2020.
#
# /etc/mosquitto/mosquitto.conf is untouched; we add drop-ins.
# /etc/mosquitto/conf.d/egnor_1883.passwd is managed locally, not in the repo.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import apt, files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    package = apt.packages(
        name="mosquitto package",
        packages=["mosquitto"],
        _sudo=True,
    )

    config = files.put(
        name="/etc/mosquitto/conf.d/egnor_1883.conf",
        src="mosquitto/files/egnor_1883.conf",
        dest="/etc/mosquitto/conf.d/egnor_1883.conf",
        mode="644",
        _sudo=True,
    )

    systemd.service(
        name="mosquitto.service enable",
        service="mosquitto.service",
        running=True,
        enabled=True,
        _sudo=True,
    )

    # Restart, not reload: `listener` isn't updated on reload signal.
    systemd.service(
        name="mosquitto restart for config change",
        service="mosquitto.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(package, config),
    )
