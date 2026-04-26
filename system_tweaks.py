#!/usr/bin/env python3
"""Apply system-level tweaks idempotently. Re-execs under sudo if needed."""

# TODO: add /etc/apt/apt.conf.d/52unattended-block-firefox

import os
import subprocess
import sys


def ensure_file(path, content):
    try:
        with open(path) as f:
            if f.read() == content:
                print(f"▫️ keep {path}")
                return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"✏️ wrote {path}")
    return True


def tweak_packagekit_memory_cap():
    # packagekitd has a long-standing leak in its apt backend; cap RSS so
    # the cgroup OOM killer reaps it before it drags the box into swap.
    path = "/etc/systemd/system/packagekit.service.d/memory-limit.conf"
    content = (
        "# Managed by system_tweaks.py\n[Service]\nMemoryMax=2G\nMemorySwapMax=0\n"
    )
    if ensure_file(path, content):
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "try-restart", "packagekit.service"], check=True)
        print("🔄 reloaded systemd, restarted packagekit if active")


TWEAKS = [
    tweak_packagekit_memory_cap,
]


if os.geteuid() != 0:
    script = os.path.abspath(__file__)
    os.execvp("sudo", ["sudo", sys.executable, script, *sys.argv[1:]])

for tweak in TWEAKS:
    print(f"== {tweak.__name__} ==")
    tweak()
