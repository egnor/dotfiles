# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Dan Egnor's personal config — both per-user dotfiles (under `homedir/`, mirroring `$HOME`) and machine-level configuration (system tweaks, nginx, etc.). Driven by [pyinfra](https://pyinfra.com/): `deploy.py` is the entrypoint, `inventory.py` lists target hosts.

## How to apply changes

```
pyinfra @local deploy.py        # this machine, no SSH
pyinfra @local deploy.py --dry  # preview without applying
pyinfra inventory.py deploy.py  # whole fleet over SSH
```

Operations files run on the controller, not on the target — pyinfra ships file content over the wire as needed and never copies the deploy scripts themselves. `@local` is pure pull (no SSH). Both modes use the same `deploy.py` and operations files.

## Layout

- `deploy.py` — entrypoint. Includes per-area operations files via `local.include`.
- `inventory.py` — hosts and groups (the "where").
- `common/` — operations that are reasonable to attempt on any machine. Each script gates its own work on facts (`LinuxName`, `Os`, etc.) so it's a no-op where it doesn't apply.
  - `user_setup.py` — symlinks every leaf under `homedir/` into `$HOME` on the target. Probes `~/source/dotfiles` and `~/dotfiles` for an existing checkout (clones if neither exists). Treats directories with a `.git` entry or that are themselves symlinks as leaves (linked as a unit, not recursed into).
  - `system_tweaks.py` — root-owned `/etc` / systemd drop-ins. Each tweak is a `files.put` (or template) followed by `systemd.daemon_reload` + `systemd.service` chained via `_if=op.did_change` so reloads happen only on real changes.
  - `files/` — content for the operations above (e.g. systemd drop-ins).
- `nginx/` — host-specific (currently only `egnor-2020`). Manages `/etc/nginx/nginx.conf` and the entries in `/etc/nginx/sites-enabled/` directly; the Debian sites-available/sites-enabled split is dropped.
  - `setup.py` gates on `Hostname` and is a no-op elsewhere.
  - `files/` mirrors the on-disk layout under `/etc/nginx/`.

## Adding a new operation

1. Decide where it lives: `common/` if it could plausibly run on more than one box (gate on a fact), a feature-named directory like `nginx/` if it's host- or service-specific.
2. Put any file content alongside the operations script under that area's `files/` directory; reference with `src="<area>/files/<name>"` (paths are resolved from the deploy directory).
3. Files that should look identical in repo and on disk get a `# Managed by pyinfra. Source: ...` header in the source file itself — no template needed. Use `files.template` (Jinja) only if you need real interpolation.
4. Wire follow-up actions (reload/restart) with `_if=op.did_change` so they only run on real changes.
5. Add `local.include("<area>/<script>.py")` to `deploy.py` if it's a new area.

## Gating idioms

- OS family: `if host.get_fact(LinuxName) in ("Ubuntu", "Debian"):`
- Specific host: `if host.get_fact(Hostname) == "egnor-2020":`
- Group membership: `if "system_admin" in host.groups:`

We deliberately do not maintain a central host-config dict; each operations file just checks for the hosts it should run on.

## Tooling expectations

`homedir/.config/mise/config.toml` pins the tools the `.zshrc` expects to find on PATH (`fd`, `gh`, `lazygit`, `neovim`, `node`, `python`, `ripgrep`, `@github/copilot-language-server`). `mise` is activated from `.zshrc` if present. If you add a shell helper that depends on a new binary, add it to the mise config in the same change.

The repo-root `mise.toml` and `pyproject.toml`/`uv.lock` set up the Python env that runs pyinfra itself (via `uv sync`).

Neovim config under `homedir/.config/nvim/` is a LazyVim starter — plugins are managed by lazy.nvim at runtime, not vendored here.
