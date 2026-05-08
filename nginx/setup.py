# Nginx config for egnor-2020. Gated on hostname so it's a no-op elsewhere.
# Drops the Debian sites-available/sites-enabled split — files go straight
# to sites-enabled/, which nginx.conf includes. Reload only on real changes.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    config_updates = [
        files.put(
            name="nginx.conf",
            src="nginx/files/nginx.conf",
            dest="/etc/nginx/nginx.conf",
            mode="644",
            _sudo=True,
        ),
        # snippets/ ships package files (fastcgi-php.conf, snakeoil.conf);
        # don't delete those — only add ours.
        files.sync(
            name="snippets/",
            src="nginx/files/snippets",
            dest="/etc/nginx/snippets",
            mode="644",
            dir_mode="755",  # also applied to dirs
            _sudo=True,
        ),
        files.sync(
            name="sites-enabled/",
            src="nginx/files/sites-enabled",
            dest="/etc/nginx/sites-enabled",
            mode="644",
            dir_mode="755",
            delete=True,  # remove anything not in repo
            _sudo=True,
        ),
    ]

    # Webroot used by certbot for HTTP-01 challenges. The acme-challenge
    # snippet (included in every :443 server) serves /.well-known/... from
    # this directory.
    files.directory(
        name="ACME webroot",
        path="/var/www/letsencrypt",
        mode="755",
        _sudo=True,
    )

    systemd.service(
        name="Reload nginx if any config changed",
        service="nginx.service",
        reloaded=True,
        _sudo=True,
        _if=any_changed(*config_updates),
    )
