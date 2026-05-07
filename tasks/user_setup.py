# Symlink every leaf under ./homedir/ into the target's $HOME.
# Replaces install.py: same rules (submodules and symlink directories are
# treated as leaves, not recursed into), but each link is a single
# idempotent files.link call instead of hand-rolled os.symlink/readlink.

import os
from pathlib import Path

from pyinfra import host
from pyinfra.facts.server import Home
from pyinfra.operations import files, git

deploy_dir = Path(__file__).resolve().parent.parent

# Where the dotfiles repo lives ON THE TARGET (so symlinks have something to
# point at). For @local that's just where this script is. For remote hosts,
# default to ~/dotfiles unless host.data.dotfiles_path overrides.
home = host.get_fact(Home) or "/root"
if host.name == "@local":
    repo_on_host = str(deploy_dir)
else:
    repo_on_host = host.data.get("dotfiles_path", f"{home}/dotfiles")
    git.repo(
        name="Clone dotfiles",
        src="https://github.com/egnor/dotfiles.git",
        dest=repo_on_host,
    )


def iter_leaves(root: Path):
    """Yields repo-relative paths for each leaf under root.
    A leaf is a regular file, a symlink, or a directory containing .git.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            full = Path(dirpath) / d
            if full.is_symlink() or (full / ".git").exists():
                dirnames.remove(d)
                filenames.append(d)
        for n in filenames:
            yield (Path(dirpath) / n).relative_to(root)


for p in sorted(iter_leaves(deploy_dir / "homedir")):
    files.link(
        name=f"symlink {p.name}",
        path=f"{home}/{p}",
        target=f"{repo_on_host}/homedir/{p}",
        create_remote_dir=True,
        force=True,  # if a regular file is in the way, back it up and replace
    )
