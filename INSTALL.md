# Installation guide

> All supported ways to install bbackup and register the `bbackup` and `bbman` commands.

---

## Recommended: uv tool

`uv tool install` installs bbackup into an isolated tool environment and links
`bbackup` and `bbman` into the uv tool bin directory.

### Install or redeploy from GitHub

If `uv` is already installed, this is the command:

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

Use the same command for first install, repair, or update from GitHub.

If `uv` is not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv tool update-shell
~/.local/bin/uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

Open a new shell after `uv tool update-shell`, then verify:

```bash
bbackup --version
bbman --version
```

### Update

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

### Uninstall

```bash
uv tool uninstall bbackup
```

---

## Advanced: system-wide uv tool links

Use this only when shared servers or root-owned cron jobs need commands under
`/usr/local/bin`:

```bash
UV="$(command -v uv)"
sudo env \
  UV_TOOL_DIR=/opt/uv/tools \
  UV_TOOL_BIN_DIR=/usr/local/bin \
  "$UV" tool install --force git+https://github.com/CruxExperts/best-backup.git

# Verify as any user
bbackup --version
bbman --version
```

Use the same command to update or repair the system-wide install. Uninstall with:

```bash
UV="$(command -v uv)"
sudo env \
  UV_TOOL_DIR=/opt/uv/tools \
  UV_TOOL_BIN_DIR=/usr/local/bin \
  "$UV" tool uninstall bbackup
```

The `UV="$(command -v uv)"` prefix avoids `env: 'uv': No such file or directory`
when sudo uses a restricted PATH.

Each user still has their own config at `~/.config/bbackup/config.yaml` and
their own log at `~/.local/share/bbackup/bbackup.log`. Only the command links
are shared.

---

## Development setup

Use this if you want to edit the source code and have changes take effect
immediately.

```bash
git clone https://github.com/CruxExperts/best-backup.git
cd best-backup

uv sync --locked
uv run bbackup --version
uv run bbman --version
```

The project requires Python 3.12 or newer. The repo includes `.python-version`
with `3.12`; uv will create `.venv` automatically when you run `uv sync --locked`.

To run commands through the development environment:

```bash
uv run bbackup backup --help
uv run bbman setup --help
```

---

## Production install from a local clone

```bash
cd /path/to/best-backup
uv tool install .
```

For an editable local tool install:

```bash
uv tool install --editable .
```

---

## Symlinks (no install, quick)

If you want to run from the repo directory without installing the package:

```bash
chmod +x bbackup.py bbman.py

sudo ln -s "$(pwd)/bbackup.py" /usr/local/bin/bbackup
sudo ln -s "$(pwd)/bbman.py" /usr/local/bin/bbman
```

For a user-only version without `sudo`:

```bash
mkdir -p ~/bin
ln -s "$(pwd)/bbackup.py" ~/bin/bbackup
ln -s "$(pwd)/bbman.py" ~/bin/bbman

export PATH="$HOME/bin:$PATH"
```

---

## Add to PATH (run directly from repo)

```bash
export PATH="$PATH:/path/to/best-backup"
chmod +x /path/to/best-backup/bbackup.py
chmod +x /path/to/best-backup/bbman.py
```

Add that export line to your shell profile to make it permanent.

---

## Python version

Python 3.12+ is required. Check the project interpreter with:

```bash
uv run python --version
```

If you need uv to create the environment with a specific interpreter:

```bash
uv sync --locked --python 3.12
```

---

## Troubleshooting

**`bbackup: command not found` after install**

Make sure the uv tool bin directory is on your PATH:

```bash
uv tool dir --bin
uv tool update-shell
```

Open a new shell after updating the shell configuration.

**Permission denied**

Use the single-user install unless you intentionally need system-wide commands:

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

**`error: externally-managed-environment` on Ubuntu 22.04+ / Debian 12+**

Do not install into the system Python. Use uv tool installs or the UV-managed
project environment:

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
uv sync --locked
```

Do not pass `--break-system-packages`; that flag bypasses OS safeguards and can
corrupt tools that depend on the system Python.

**Dependencies look stale**

Refresh the project environment from the lockfile:

```bash
uv sync --locked
```

---

## Post-install setup

Once the commands are available, run the setup wizard:

```bash
bbman setup
```

See [QUICKSTART.md](QUICKSTART.md) for what to do next.

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
