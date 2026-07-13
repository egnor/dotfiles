# Home directory setup that egnor likes.
# Symlink every leaf under files/ into the target's $HOME.

import os
from pathlib import Path
from pyinfra import host
from pyinfra.facts.files import Directory, File
from pyinfra.facts.server import Home, LsbRelease, Os
from pyinfra.operations import files, git, server


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
    repo_op = git.repo(
        name="Clone or update dotfiles repo",
        src="https://github.com/egnor/dotfiles.git",
        dest=repo_on_host,
    )

    return repo_on_host, repo_op


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


# egnor's dotfiles are Linux-oriented today; some leaves assume Linux paths or
# tools (fontconfig, kitty, the LazyVim/mise toolchain). Gate the whole area on
# Linux so it cleanly skips macOS, router shells, or any other non-Linux target.
# Generalise if/when we get there.
if host.get_fact(Os) == "Linux":
    # Some files must be copied, not linked to work (eg. .forward)
    files.sync(src="user/copy-files", dest=host.get_fact(Home), delete=False)

    # For other files, make symlinks so any edits are made to the repo
    repo_on_host, repo_op = setup_repo_on_host()
    link_tree("files-linux", repo_on_host)

    # "Modern" Linux hosts (Ubuntu 20.04+) additionally get tools whose prebuilt
    # binaries need a recent glibc — see
    # user/files-linux-modern/.config/mise/conf.d/.
    lsb = host.get_fact(LsbRelease) or {}
    if lsb.get("id") == "Ubuntu":
        if int(lsb.get("release", "").split(".")[0]) >= 20:
            link_tree("files-linux-modern", repo_on_host)

    # Now that the symlinks (incl. .config/mise/*) are in place, reconcile
    # mise-managed CLI tools whenever the repo updated.
    mise_bin = f"{host.get_fact(Home)}/.local/bin/mise"
    if host.get_fact(File, path=mise_bin):
        server.shell(
            name="Install mise-managed CLI tools",
            commands=[f"{mise_bin} install"],
            _if=repo_op.did_change,
        )
