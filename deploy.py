# Top-level PyInfra deploy: runs for every host in the inventory.
#
#   pyinfra @local deploy.py         # this machine, no SSH
#   pyinfra eacs.io deploy.py        # remote machine over SSH
#   pyinfra eacs.io deploy.py --dry  # preview without applying

from pyinfra import local

local.include("common/user_setup.py")
local.include("common/system_tweaks.py")
local.include("nginx/setup.py")
