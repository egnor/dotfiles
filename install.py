#!/usr/bin/env python3

import os
import os.path
import stat

def update_links(source_rel, home_rel):
    normjoin = lambda *paths: os.path.normpath(os.path.join(*paths))

    source_abs = normjoin(os.getcwd(), os.path.dirname(__file__), source_rel)
    home_abs = normjoin(os.environ["HOME"], home_rel)
    source_to_home = os.path.relpath(source_abs, start=home_abs)
    links = {f: normjoin(source_to_home, f) for f in os.listdir(source_abs)}

    os.makedirs(home_abs, exist_ok=True)
    for existing_name in sorted(os.listdir(home_abs)):
        existing_abs = normjoin(home_abs, existing_name)
        try:
            existing_link = os.readlink(existing_abs)
        except OSError:
            continue

        tilde_rel = normjoin("~", home_rel, existing_name)
        desired_link = links.pop(existing_name, None)
        if not desired_link and "dotfiles" in existing_link:
            print(f"*remove* {tilde_rel} (was => {existing_link})")
            os.remove(existing_abs)
        elif not desired_link:
            print(f"(ignore {tilde_rel} => {existing_link})")
        elif desired_link == existing_link:
            print(f"(keep {tilde_rel} => {existing_link})")
        else:
            print(
                f"*update* {tilde_rel} => {desired_link} "
                f"(was {existing_link})")
            os.remove(existing_abs)
            os.symlink(desired_link, existing_abs)

    for new_name, new_link in sorted(links.items()):
        tilde_rel = normjoin("~", home_rel, new_name)
        print(f"*link* {tilde_rel} => {new_link}")
        target = normjoin(home_abs, new_name)
        if os.path.isdir(target) and not os.listdir(target):
            os.rmdir(normjoin(home_abs, new_name))
        os.symlink(new_link, normjoin(home_abs, new_name))


update_links("homedir", ".")
update_links("dotconfig", ".config")
update_links("dotssh", ".ssh")
