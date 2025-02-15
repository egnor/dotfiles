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

for source_sub, dirs, names in os.walk(source_abs):
    links = {}

    sub_rel = os.path.relpath(source_sub, start=source_abs)
    home_sub = os.path.join(home_abs, sub_rel)
    if not (dirs or names):
        sys.exit(f"EMPTY: {source_sub}")

    print(f"📂 {sub_rel}")

    walk_dirs, dirs[:] = dirs[:], []
    for dir_name in walk_dirs:
        dir_abs = normjoin(source_sub, dir_name)
        if os.path.islink(dir_abs):
            print(f"📎 symlink dir: {dir_name}")
            names.append(dir_name)
        elif os.path.exists(normjoin(dir_abs, ".git")):
            print(f"📦 git submodule: {dir_name}")
            names.append(dir_name)
        else:
            dirs.append(dir_name)

    home_to_source_sub = os.path.relpath(source_sub, start=home_sub)
    for name in names:
        links[normjoin(sub_rel, name)] = normjoin(home_to_source_sub, name)

    for old_name in os.listdir(home_sub) if os.path.isdir(home_sub) else []:
        old_abs = normjoin(home_sub, old_name)
        try:
            old_link = os.readlink(old_abs)
        except OSError:
            continue  # not a symlink, ignore

        old_rel = normjoin(sub_rel, old_name)
        old_tilde = normjoin("~", old_rel)
        desired_link = links.pop(old_rel, None)
        if desired_link == old_link:
            print(f"▫️ keep {old_tilde} => {old_link}")
        elif not desired_link and "dotfiles" in old_link:
            print(f"🗑️ REMOVE {old_tilde} (was => {old_link})")
            os.remove(old_abs)
        elif desired_link:
            print(
                f"🔄 UPDATE {old_tilde} => {desired_link} "
                f"(was {old_link})")
            os.remove(old_abs)
            os.symlink(desired_link, old_abs)

    for new_name, new_link in sorted(links.items()):
        tilde_rel = normjoin("~", new_name)
        target = normjoin(home_abs, new_name)
        if os.path.isdir(target) and not os.listdir(target):
            print(f"🗑️ RMDIR {new_name}")
            os.rmdir(normjoin(home_abs, new_name))

        parent = os.path.dirname(target)
        if not os.path.isdir(parent):
            print(f"📁 MKDIR {parent}")
            os.makedirs(parent, exist_ok=True)

        print(f"🔗 SYMLINK {tilde_rel} => {new_link}")
        os.symlink(new_link, normjoin(home_abs, new_name))

    if names:
        print()
