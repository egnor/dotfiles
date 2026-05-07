# Nginx config for egnor-2020. Gated on hostname so it's a no-op elsewhere.
# Drops the Debian sites-available/sites-enabled split — files go straight
# to sites-enabled/, which nginx.conf includes. Reload only on real changes.

from pyinfra import host
from pyinfra.facts.server import Hostname
from pyinfra.operations import files, systemd
from pyinfra.operations.util import any_changed

if host.get_fact(Hostname) == "egnor-2020":
    SITES = ["anaulin", "drain-teaser", "egnor", "leftout"]

    nginx_conf = files.put(
        name="nginx.conf",
        src="nginx/files/nginx.conf",
        dest="/etc/nginx/nginx.conf",
        mode="644",
        _sudo=True,
    )

    site_changes = [
        files.put(
            name=f"site: {site}",
            src=f"nginx/files/sites-enabled/{site}",
            dest=f"/etc/nginx/sites-enabled/{site}",
            mode="644",
            _sudo=True,
        )
        for site in SITES
    ]

    systemd.service(
        name="Reload nginx if any config changed",
        service="nginx.service",
        reloaded=True,
        _sudo=True,
        _if=any_changed(nginx_conf, *site_changes),
    )
