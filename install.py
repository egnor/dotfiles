#!/usr/bin/env python3

import os
import os.path
import stat
import sys

def normjoin(*paths):
    return os.path.normpath(os.path.join(*paths))

home_abs = os.environ["HOME"]
source_abs = normjoin(os.getcwd(), os.path.dirname(__file__), "homedir")
home_to_source = os.path.relpath(source_abs, start=home_abs)

links = {}
for source_sub, subdirs, names in os.walk(source_abs):
    sub_rel = os.path.relpath(source_sub, start=source_abs)
    home_sub = os.path.join(home_abs, sub_rel)
    home_to_source_sub = os.path.relpath(source_sub, start=home_sub)
    if not (subdirs or names):
        sys.exit(f"EMPTY: {source_sub}")
    elif ".git" in names:
        links[sub_rel] = home_to_source_sub
        subdirs[:] = []  # Prune subdirectories
    else:
        for name in names:
            links[normjoin(sub_rel, name)] = normjoin(home_to_source_sub, name)

os.makedirs(home_abs, exist_ok=True)
for home_sub, subdirs, names in os.walk(home_abs):
    sub_rel = os.path.relpath(home_sub, start=home_abs)
    for name in names:
        existing_abs = normjoin(home_sub, name)
        try:
            existing_link = os.readlink(existing_abs)
        except OSError:
            continue

        name_rel = normjoin(sub_rel, name)
        tilde_rel = normjoin("~", name_rel)
        desired_link = links.pop(name_rel, None)
        if desired_link == existing_link:
            print(f"(keep {tilde_rel} => {existing_link})")
        elif not desired_link and "dotfiles" in existing_link:
            print(f"*remove* {tilde_rel} (was => {existing_link})")
            os.remove(existing_abs)
        elif desired_link:
            print(
                f"*update* {tilde_rel} => {desired_link} "
                f"(was {existing_link})")
            os.remove(existing_abs)
            os.symlink(desired_link, existing_abs)

for new_name, new_link in sorted(links.items()):
    tilde_rel = normjoin("~", new_name)
    target = normjoin(home_abs, new_name)
    if os.path.isdir(target) and not os.listdir(target):
        print(f"*rmdir* {new_name}")
        os.rmdir(normjoin(home_abs, new_name))

    parent = os.path.dirname(target)
    if not os.path.isdir(parent):
        print(f"*mkdir* {parent}")
        os.makedirs(parent, exist_ok=True)

    print(f"*link* {tilde_rel} => {new_link}")
    os.symlink(new_link, normjoin(home_abs, new_name))
