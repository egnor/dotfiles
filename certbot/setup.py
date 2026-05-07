# Certbot defaults + post-renewal nginx reload hook for the public web host.
# The Debian/Ubuntu certbot package ships and enables `certbot.timer`
# (twice-daily `certbot renew`) — we don't manage the timer, just the
# config it uses.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import files

if host.get_fact(Hostname) == "egnor-2020":
    files.put(
        name="certbot: cli.ini",
        src="certbot/files/cli.ini",
        dest="/etc/letsencrypt/cli.ini",
        mode="644",
        _sudo=True,
    )

    files.put(
        name="certbot: reload-nginx deploy hook",
        src="certbot/files/reload-nginx",
        dest="/etc/letsencrypt/renewal-hooks/deploy/reload-nginx",
        mode="755",
        _sudo=True,
    )
