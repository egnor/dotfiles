#!/usr/bin/env python3
# Managed by pyinfra. Source: dotfiles/netdata/files.parent/netdata-ping-healthchecks.py
#
# Checks netdata liveness and pings an external monitor (healthchecks.io).
# Run periodically from a systemd timer (netdata-ping-healthchecks.timer)

from urllib.request import urlopen

netdata_url = "http://127.0.0.1:19998/api/v1/info"
ping_url = "https://hc-ping.com/22f0a97c-803e-4f40-8efe-66756bdaf5d8"
try:
    urlopen(netdata_url, timeout=20).read()
except Exception:
    urlopen(ping_url + "/fail", timeout=20).read()
    raise
else:
    urlopen(ping_url, timeout=20).read()
