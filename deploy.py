# Top-level PyInfra deploy: runs for every host in the inventory.
#
#   pyinfra @local deploy.py            # this machine, no SSH
#   pyinfra inventory.py deploy.py      # whole fleet
#   pyinfra inventory.py deploy.py --dry  # preview without applying

from pyinfra import host, local

local.include("tasks/dotfiles_symlinks.py")

if "system_admin" in host.groups:
    local.include("tasks/system_tweaks.py")
