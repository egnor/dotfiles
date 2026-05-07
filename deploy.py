# Top-level PyInfra deploy: runs for every host in the inventory.
#
#   pyinfra @local deploy.py         # this machine, no SSH
#   pyinfra eacs.io deploy.py        # remote machine over SSH
#   pyinfra eacs.io deploy.py --dry  # preview without applying

from pyinfra import local

local.include("nginx/setup.py")
local.include("certbot/setup.py")
local.include("user/setup.py")
local.include("tweaks/setup.py")
