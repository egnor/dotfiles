# PyInfra inventory: hosts and groups for `pyinfra inventory.py deploy.py`.
#
# `@local` runs without SSH against this machine — useful for laptops that
# pull their own config. Add SSH hosts as plain strings; per-host data goes
# in a (name, {...}) tuple and shows up as `host.data.<key>` in operations.

laptops = [
    "@local",
    # ("other-laptop", {"ssh_user": "egnor", "dotfiles_path": "/home/egnor/dotfiles"}),
]

servers = [
    # "mail.ofb.net",
    # "web.ofb.net",
]

pis = [
    # "pi-livingroom.lan",
]

# Convenience group: every box I administer (gets system_tweaks applied).
system_admin = laptops + servers + pis
