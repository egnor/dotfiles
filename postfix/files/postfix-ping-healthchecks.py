#!/usr/bin/env python3
# Managed by pyinfra. Source: dotfiles/postfix/files/postfix-ping-healthchecks.py
#
# End-to-end test of outgoing email, evaluated externally (healthchecks.io).
# Run periodically from a systemd timer (postfix-ping-healthchecks.timer)

import subprocess

# Uses a local domain to get DKIM, avoid SRS rewriting, and catch bounces.
sender = "mail-deadman@eacs.io"
dest = "1df2906b-6bc7-4157-bd32-8f9bd8bbed24@hc-ping.com"
headers = f"From: {sender}\nTo: {dest}\nSubject: probe\n\n"
body = "By: dotfiles/postfix/files/postfix-ping-healthchecks.py\n"
args = ["sendmail", "-f", sender, "--", dest]
subprocess.run(args, input=headers + body, text=True, check=True)
