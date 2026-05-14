# Home directory setup that egnor likes.
# Symlink every leaf under files/ into the target's $HOME.

import os
from pathlib import Path
from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Home, LsbRelease
from pyinfra.operations import files, git


def setup_repo_on_host():
    # Probe known locations on the target; first existing checkout wins.
    # If none exist, fall back to ~/dotfiles (where git.repo will clone fresh).
    home = host.get_fact(Home)
    candidates = [f"{home}/source/dotfiles", f"{home}/dotfiles"]
    repo_on_host = next(
        (p for p in candidates if host.get_fact(Directory, path=f"{p}/.git")),
        f"{home}/dotfiles",
    )

    # Clones if missing, pulls if present (no-op when local tip == remote tip).
    git.repo(
        name="Clone or update dotfiles repo",
        src="https://github.com/egnor/dotfiles.git",
        dest=repo_on_host,
    )

    return repo_on_host


def link_tree(tree, repo_on_host):
    def iter_leaves(root: Path):
        """Yields repo-relative paths for each linkable target under root."""
        for dirpath, dirnames, filenames in os.walk(root):
            for d in list(dirnames):
                full = Path(dirpath) / d
                if full.is_symlink() or (full / ".git").exists():
                    dirnames.remove(d)
                    filenames.append(d)
            for n in filenames:
                yield (Path(dirpath) / n).relative_to(root)

    tree_local = Path(__file__).parent / tree
    home_on_host = host.get_fact(Home)
    for rel in sorted(iter_leaves(tree_local)):
        files.link(
            name=f"{tree}/{rel}",
            path=f"{home_on_host}/{rel}",
            target=f"{repo_on_host}/user/{tree}/{rel}",
            create_remote_dir=True,
        )


# Some files must be copied, not linked to work (eg. .forward)
files.sync(src="user/copy-files", dest=host.get_fact(Home), delete=False)

# For other files, make symlinks to any edits are made to the repo
repo_on_host = setup_repo_on_host()
link_tree("files", repo_on_host)

# "Modern" hosts (Ubuntu 20.04+) additionally get tools whose prebuilt
# binaries need a recent glibc — see user/files-modern/.config/mise/conf.d/.
lsb = host.get_fact(LsbRelease) or {}
if lsb.get("id") == "Ubuntu" and int(lsb.get("release", "").split(".")[0]) >= 20:
    link_tree("files-modern", repo_on_host)
