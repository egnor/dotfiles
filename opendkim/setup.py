# OpenDKIM milter for egnor-2020 — signs outgoing mail for the four
# domains hosted here, verifies inbound. Wired into postfix via
# `smtpd_milters = local:opendkim/opendkim.sock` in postfix/main.cf.
#
# The .private keys under /etc/dkimkeys/ stay out of the repo (live
# secrets). To rotate a key: `opendkim-genkey -d <domain> -s mail -D
# /etc/dkimkeys/`, publish the .txt selector record in DNS, then
# `systemctl restart opendkim`.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    opendkim_conf = files.put(
        name="opendkim: opendkim.conf",
        src="opendkim/files/opendkim.conf",
        dest="/etc/opendkim.conf",
        mode="644",
        _sudo=True,
    )

    # /etc/dkimkeys/ is mode 700 owned by opendkim — files.put runs as root
    # via sudo so it can write inside, then we re-set owner=opendkim.
    key_table = files.put(
        name="opendkim: key.table",
        src="opendkim/files/key.table",
        dest="/etc/dkimkeys/key.table",
        user="opendkim",
        group="opendkim",
        mode="644",
        _sudo=True,
    )

    signing_table = files.put(
        name="opendkim: signing.table",
        src="opendkim/files/signing.table",
        dest="/etc/dkimkeys/signing.table",
        user="opendkim",
        group="opendkim",
        mode="644",
        _sudo=True,
    )

    trusted_hosts = files.put(
        name="opendkim: trusted.hosts",
        src="opendkim/files/trusted.hosts",
        dest="/etc/dkimkeys/trusted.hosts",
        user="opendkim",
        group="opendkim",
        mode="644",
        _sudo=True,
    )

    systemd.service(
        name="opendkim: restart on config change",
        service="opendkim.service",
        restarted=True,
        _sudo=True,
        _if=any_changed(opendkim_conf, key_table, signing_table, trusted_hosts),
    )
