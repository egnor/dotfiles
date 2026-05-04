# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Dan Egnor's personal dotfiles. Files under `homedir/` mirror the layout of `$HOME` — e.g. `homedir/.zshrc` becomes `~/.zshrc`. There is no build system; "installing" means creating symlinks from `$HOME` into this repo.

## Install mechanism (`install.py`)

Run with `./install.py` from the repo. The script walks `homedir/` and, for each file, creates a relative symlink at the corresponding path under `$HOME`. Understanding its rules matters before moving files around:

- **Relative symlinks.** Targets are computed via `os.path.relpath`, so the repo can live anywhere as long as `$HOME` and the repo share an ancestor. Do not rewrite to absolute paths.
- **Submodule / symlink leaves.** A directory inside `homedir/` is linked as a whole (not recursed into) if it contains a `.git` entry or is itself a symlink. This is how e.g. a plugin checkout gets linked as a single unit. If you add a new submodule under `homedir/`, you get this behavior automatically.
- **Cleanup is scoped.** Existing symlinks under `$HOME` are only removed when their target path contains the substring `"dotfiles"`. Non-symlink files and unrelated symlinks are left alone. This is deliberate — don't broaden it.
- **Empty dirs get replaced.** If the target path in `$HOME` is an empty directory, it's `rmdir`'d before the symlink is created.

## Tooling expectations

`homedir/.config/mise/config.toml` pins the tools the `.zshrc` expects to find on PATH (`fd`, `gh`, `lazygit`, `neovim`, `node`, `python`, `ripgrep`, `@github/copilot-language-server`). `mise` is activated from `.zshrc` if present. If you add a shell helper that depends on a new binary, add it to the mise config in the same change.

Neovim config under `homedir/.config/nvim/` is a LazyVim starter — plugins are managed by lazy.nvim at runtime, not vendored here.

## `system_tweaks.py`

Idempotent applier for root-owned system config (systemd drop-ins, `/etc/` files, etc.) that doesn't belong under `homedir/`. Re-execs itself under sudo if not already root. Each tweak is a function in the `TWEAKS` list; the shared `ensure_file(path, content)` helper writes only when content differs and returns a change flag so callers can gate follow-up actions (`systemctl daemon-reload`, etc.) on real changes. Add new tweaks by writing a function and appending it to `TWEAKS`.
