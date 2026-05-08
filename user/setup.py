# Home directory setup that egnor likes.
# Symlink every leaf under files/ into the target's $HOME.

import os
from pathlib import Path
from pyinfra import host
from pyinfra.facts.files import Directory
from pyinfra.facts.server import Home
from pyinfra.operations import files, git


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

files_dir = Path(__file__).parent / "files"
for rel in sorted(iter_leaves(files_dir)):
    files.link(
        name=str(rel),
        path=f"{home}/{rel}",
        target=f"{repo_on_host}/user/files/{rel}",
        create_remote_dir=True,
    )
