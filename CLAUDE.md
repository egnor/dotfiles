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

## `tv_power.py`

Standalone Raspberry Pi utility, unrelated to the dotfiles install flow. Uses `libcec` to drive TV power and listens on the GNOME session bus (`org.gnome.ScreenSaver` + `org/gnome/Mutter/DisplayConfig`) to wake the TV when the screen unblanks. The `tv_power.desktop` autostart entry launches it with `--dbus`. Modes (`--on`, `--off`, `--dbus`, `--dbus_test`) are mutually exclusive. Requires the `cec`, `dbus`, and `gi` Python bindings from the system packages — it is not pip-installable on its own.
