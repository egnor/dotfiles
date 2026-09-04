#!/usr/bin/env python3
# Managed by pyinfra. Source: dotfiles/netdata/files.parent/netdata-ping-healthchecks.py
#
# Checks netdata liveness and pings an external monitor (healthchecks.io).
# Run periodically from a systemd timer (netdata-ping-healthchecks.timer)
#
# Each step retries a few times so a netdata restart (deploy) or a passing
# hc-ping.com 502 doesn't fail the unit and trip the systemdunits alert.
# Worst case runtime is well under the timer's 5 minute period; the service's
# TimeoutStartSec is set with that in mind.

import sys
import time
from urllib.request import urlopen

netdata_url = "http://127.0.0.1:19998/api/v1/info"
ping_url = "https://hc-ping.com/22f0a97c-803e-4f40-8efe-66756bdaf5d8"


def fetch(url, tries, wait):
    for attempt in range(1, tries + 1):
        try:
            return urlopen(url, timeout=20).read()
        except Exception as e:
            print(f"attempt {attempt}/{tries} failed: {e}", file=sys.stderr)
            if attempt == tries:
                raise
            time.sleep(wait)


try:
    fetch(netdata_url, tries=3, wait=10)  # rides out a netdata restart
except Exception:
    fetch(ping_url + "/fail", tries=3, wait=30)
    raise
else:
    fetch(ping_url, tries=3, wait=30)
