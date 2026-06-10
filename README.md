<div align="center">

# 🗄️ bbackup

**Back up Docker containers and host filesystems — encrypted, incremental, and agent-ready.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.8.2-6366f1?style=flat-square)](CHANGELOG.md)

[Quick start](#quick-start) · [Filesystem backup](#filesystem-backup) · [Agent integration](#agent-integration) · [CLI reference](#cli-reference) · [Docs](#documentation)

</div>

![bbackup backup pipeline showing Docker, filesystem, database, encryption, verification, and remote storage destinations](docs/assets/bbackup-hero.png)

---

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

`uv` handles the isolated tool environment automatically. This one command works for first install and redeploy/update from GitHub. See [Installation](#installation) if you need to install `uv` first, or for advanced system-wide `/usr/local/bin` deployment.

---

## Why bbackup

Run `bbackup backup` and you get an interactive container picker, a live BTOP-style dashboard while the backup runs, and a finished artifact that can be verified, encrypted, and shipped to Google Drive, SFTP, or a local path. Point it at `/srv/data` and it backs that up too, with gitignore-style excludes. The companion `bbman` command handles setup, health checks, dependency installs, and self-updates so day-to-day maintenance stays out of the way.

Every command speaks structured JSON, making it compatible with AI agents out of the box: set two env vars, run `bbackup skills`, and drive the entire tool with `--input-json`.

> [!TIP]
> Use `--dry-run --output json` before destructive restore work or scheduled backup changes. The JSON plan is designed for both humans and automation.

## Backup flow

```mermaid
flowchart LR
    docker[Docker containers<br/>volumes • configs • networks]
    fs[Host filesystems<br/>paths • excludes]
    manifest[backup_manifest.json<br/>sizes • SHA-256 • item results]
    encrypt[Encryption<br/>AES-256-GCM or RSA-4096]
    upload[Remote upload<br/>local • SFTP • rclone]
    restore[Restore preflight<br/>manifest verification]

    docker --> manifest
    fs --> manifest
    manifest --> encrypt
    encrypt --> upload
    manifest --> restore
```

---

## Features

| | Feature | Description |
|:---:|:---|:---|
| 🖥️ | **Rich TUI** | BTOP-style live dashboard with real-time transfer metrics |
| 🐳 | **Docker backup** | Containers, volumes, networks, and configs in one shot |
| 📁 | **Filesystem backup** | Back up any host path recursively with gitignore-style excludes |
| ⚡ | **Incremental backups** | rsync `--link-dest` so unchanged data is hardlinked, not copied |
| 🔐 | **Encryption** | AES-256-GCM (symmetric) or RSA-4096 (asymmetric) at rest |
| ☁️ | **Remote storage** | Google Drive via rclone, SFTP, or local directory |
| ♻️ | **Rotation** | Time-based daily/weekly/monthly retention with quota enforcement |
| 📦 | **Solid archive** | Optional single tarball (and optional whole-file encryption) for upload so remotes get one file instead of many |
| ↩️ | **Full restore** | Containers, volumes, networks, and filesystem paths; restore from directory or solid archive file |
| 📦 | **Backup sets** | Named groups of containers defined in config for repeatable runs |
| 🤖 | **Agent-friendly CLI** | JSON I/O, `--input-json`, `--dry-run`, and skill discovery on every command |
| 🛠️ | **Management CLI** | `bbman` for setup, health, updates, cleanup, and diagnostics |

---

## Requirements

- Python 3.12+
- Docker (with socket access for your user)
- `rsync` (system package — used for volume and filesystem backups)
- `rclone` (optional, for Google Drive)

---

## Installation

`uv` handles the tool environment automatically.

### Install or redeploy from GitHub

Run this when `uv` is already installed:

```bash
uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

It creates an isolated uv tool environment and links `bbackup` and `bbman` into the uv tool bin directory. The `--force` flag makes the same command safe for first install, repair, and redeploy/update.

If `uv` is not installed yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv tool update-shell
~/.local/bin/uv tool install --force git+https://github.com/CruxExperts/best-backup.git
```

Open a new shell after `uv tool update-shell` so `bbackup` and `bbman` are on your PATH.

### Advanced: system-wide links

Most installs should use the uv tool command above. If `/usr/local/bin/bbackup`
and `/usr/local/bin/bbman` must be shared by every user or a root-owned
scheduler, see [INSTALL.md](INSTALL.md#advanced-system-wide-uv-tool-links).

For development setup, local source installs, and uninstall instructions, see [INSTALL.md](INSTALL.md).

---

## Quick start

```bash
# First-time setup: checks Docker, installs deps, creates config
bbman setup

# Interactive backup with live TUI
bbackup backup

# Target specific containers
bbackup backup --containers myapp mydb

# Back up a host filesystem path
bbackup backup --paths /srv/data

# Non-interactive mode (cron or agent)
BBACKUP_OUTPUT=json BBACKUP_NO_INTERACTIVE=1 bbackup backup --backup-set production
```

See [QUICKSTART.md](QUICKSTART.md) for a full walk-through: config, remote storage, encryption setup, and more.

---

## Integrity And Upload Safety

Each non-cancelled backup writes `backup_manifest.json` with the requested scope, filesystem source paths, volume artifact names, item results, errors, file sizes, and SHA-256 hashes. Restore verifies the manifest when present and fails before mutation if files are missing, changed, unlisted, or outside the backup root.

Local, SFTP, and rclone uploads write to `.partial` destinations first and promote to the final backup name only after the copy succeeds. When encryption succeeds, plaintext staging is removed so local backup artifacts match the encrypted output.

---

## Configuration

bbackup checks these locations in order:

1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml`

A fully annotated template is in [`config.yaml.example`](config.yaml.example). The minimal setup:

```yaml
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    production:
      containers: [myapp, mydb, nginx]
      scope:
        volumes: true
        configs: true

remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

For rclone remotes you can optionally set `rclone_options.transfers` and `rclone_options.checkers` (or top-level `rclone.default_options`) to tune upload concurrency; both accept 1–32, default 8. See [config.yaml.example](config.yaml.example) and [docs/architecture.md](docs/architecture.md#rclone-options).

### Filesystem backup

Add a `filesystem:` section to back up arbitrary host paths:

```yaml
filesystem:
  home-data:
    description: "Important home directory data"
    targets:
      - name: documents
        path: /home/user/Documents
        enabled: true
        excludes:
          - "*.tmp"
          - ".cache/"
          - "node_modules/"
```

Run a named filesystem set:

```bash
bbackup backup --filesystem-set home-data
```

Or pass paths directly, no config needed:

```bash
bbackup backup --paths /home/user/docs /srv/data --exclude "*.tmp"
```

---

## CLI reference

<details>
<summary><strong>bbackup commands</strong></summary>

```bash
# Docker backup
bbackup backup                                         # Interactive backup with TUI
bbackup backup --backup-set production                 # Named backup set from config
bbackup backup --containers app db                     # Specific containers
bbackup backup --incremental                           # rsync --link-dest mode
bbackup backup --config-only                           # Skip volumes
bbackup backup --volumes-only                          # Skip configs
bbackup backup --no-networks                           # Skip network configs
bbackup backup --remote gdrive                         # Upload to specific remote

# Filesystem backup
bbackup backup --paths /home/user/docs /srv/data       # Back up specific paths
bbackup backup --paths /home/user/docs --exclude "*.tmp"
bbackup backup --filesystem-set home-data              # Named set from config

# Restore
bbackup restore --backup-path /path/to/backup --all
bbackup restore --backup-path /path --containers app --rename app:app_v2
bbackup restore --backup-path /path --filesystem documents \
  --filesystem-destination /home/user/docs

# Inspect
bbackup list-containers
bbackup list-backup-sets
bbackup list-filesystem-sets
bbackup list-backups
bbackup list-remote-backups --remote gdrive

# Setup
bbackup init-config
bbackup init-encryption --method asymmetric --algorithm rsa-4096

# Agent / non-interactive (available on every command)
bbackup list-containers --output json
bbackup backup --containers app --input-json '{"incremental":true}'
bbackup backup --containers app --dry-run --output json
bbackup skills                          # discover all capabilities
bbackup skills docker-backup            # step-by-step guide + JSON schemas
```

</details>

<details>
<summary><strong>bbman commands</strong></summary>

```bash
bbman setup                                          # First-time setup wizard
bbman setup --no-interactive                         # Skip wizard (agent mode)
bbman health                                         # Docker, tools, config health check
bbman health --output json
bbman check-deps                                     # Check dependencies
bbman check-deps --install                           # Install missing packages
bbman validate-config                                # Parse and validate config
bbman status                                         # Backup history and totals
bbman status --output json
bbman cleanup                                        # Clean staging dirs and old logs
bbman cleanup --yes                                  # Skip confirmation (agent mode)
bbman diagnostics                                    # Generate diagnostic report
bbman diagnostics --report-file /tmp/report.txt      # Save to file
bbman check-updates                                  # Check for newer version
bbman update                                         # Self-update from repo
bbman update --yes                                   # Skip confirmation (agent mode)
bbman repo-url --url URL                             # Set the update source URL
bbman run backup --containers app                    # Run bbackup through the wrapper
bbman skills                                         # Discover bbman capabilities
bbman skills maintenance                             # Step-by-step maintenance guide
```

</details>

---

## Agent integration

bbackup and bbman are natively compatible with AI agents. Every command supports structured JSON I/O, progressive skill discovery, and non-interactive execution without extra configuration.

### Environment variables

Set these once and every subprocess inherits them:

```bash
export BBACKUP_OUTPUT=json           # all commands emit a JSON envelope
export BBACKUP_NO_INTERACTIVE=1      # no TUI, no prompts, no pagers
```

| Variable | Effect |
|:---|:---|
| `BBACKUP_OUTPUT=json` | All commands emit JSON envelope without `--output json` |
| `BBACKUP_NO_INTERACTIVE=1` | Suppresses TUI, prompts, and pagers system-wide |

### Skill discovery (JSON and Markdown)

```bash
bbackup skills                           # level-0: all skill IDs + summaries (JSON)
bbackup skills docker-backup             # level-1: steps, schemas, examples (JSON)
bbackup skills --format markdown         # full Markdown skills catalog
bbman skills                             # level-0 skills for bbman (JSON)
bbman skills maintenance                 # maintenance skill (JSON)
bbman skills --format markdown           # full Markdown skills catalog
```

Level-0 JSON output:

```json
{
  "cli": "bbackup",
  "version": "1.8.2",
  "agent_hint": "Set BBACKUP_OUTPUT=json and BBACKUP_NO_INTERACTIVE=1 for fully non-interactive use.",
  "skills": [
    {"id": "docker-backup",     "summary": "Back up Docker containers, volumes, networks, and configs.", "common": true},
    {"id": "filesystem-backup", "summary": "Back up arbitrary host filesystem paths with gitignore-style excludes.", "common": true},
    {"id": "restore",           "summary": "Restore containers, volumes, networks, or filesystem paths from a backup.", "common": true}
  ]
}
```

### JSON envelope

Every command in JSON mode emits exactly this to **stdout**. All progress and diagnostic text goes to **stderr**.

```json
{
  "schema_version": "1",
  "command": "backup",
  "success": true,
  "data": {},
  "errors": []
}
```

- `schema_version` bumps only on breaking changes — additive fields are always safe.
- `errors` is always present; non-empty means `success: false`.
- A non-zero exit code always accompanies `success: false`.

### `--input-json` parameter passing

Pass all parameters as a single flat JSON object. Keys use underscores (hyphens converted). The object merges over any CLI flags already provided.

```bash
bbackup restore \
  --input-json '{"backup_path":"/tmp/bbackup/backup_20260227","containers":["myapp"],"dry_run":true}' \
  --output json
```

Unknown keys are silently ignored — forward-compatible by design.

### Dry-run / pre-flight

```bash
bbackup backup --containers myapp --dry-run --output json
```

```json
{
  "schema_version": "1",
  "command": "backup",
  "success": true,
  "data": {
    "dry_run": true,
    "would_backup": {
      "containers": ["myapp"],
      "filesystem_targets": [],
      "remotes": [],
      "incremental": false,
      "scope": {"volumes": true, "configs": true, "networks": true}
    }
  },
  "errors": []
}
```

### Exit codes

| Code | Meaning |
|:---:|:---|
| `0` | Fully successful |
| `1` | Bad argument, missing param, or invalid `--input-json` |
| `2` | Config not found or fails validation |
| `3` | Docker unreachable, rsync/rclone missing, or key generation failed |
| `4` | Partial: some items succeeded, some failed |
| `5` | Operation cancelled by user or agent |

> [!TIP]
> For agent workflows, set `BBACKUP_OUTPUT=json` and `BBACKUP_NO_INTERACTIVE=1` globally, then use `bbackup skills` to discover what's available before issuing commands.

---

## Encryption

Two modes are available:

**Symmetric — AES-256-GCM:** One key encrypts and decrypts. Good for single-server setups.

```bash
bbackup init-encryption --method symmetric
```

**Asymmetric — RSA-4096:** Public key encrypts, private key decrypts. Better for multi-server setups where backup and restore run on separate machines.

```bash
bbackup init-encryption --method asymmetric --algorithm rsa-4096
```

The public key can live on GitHub:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: github:YOUR_USERNAME/gist:YOUR_GIST_ID
    private_key: ~/.config/bbackup/backup_private.pem
```

Full details in [docs/encryption.md](docs/encryption.md).

---

## TUI keyboard controls

| Key | Action |
|:---:|:---|
| `Q` | Quit / cancel backup |
| `P` | Pause / resume |
| `S` | Skip current item |
| `H` | Help |

---

## Project structure

```
best-backup/
├── bbackup/
│   ├── cli.py                # bbackup CLI entry point
│   ├── cli_utils.py          # JSON envelope, exit codes, shared decorators
│   ├── skills.py             # Skill descriptors for agent discovery
│   ├── config.py             # Config loading and all dataclasses
│   ├── docker_backup.py      # Docker backup via temp Alpine containers
│   ├── filesystem_backup.py  # Host filesystem backup via rsync
│   ├── backup_runner.py      # Backup workflow orchestration
│   ├── restore.py            # Restore operations
│   ├── tui.py                # Rich TUI and BackupStatus tracking
│   ├── remote.py             # Remote storage (local / rclone / SFTP)
│   ├── rotation.py           # Retention policies and quota cleanup
│   ├── encryption.py         # AES-256-GCM + RSA encryption
│   ├── logging.py            # Rotating file logger
│   ├── bbman_entry.py        # Console script shim for bbman
│   └── management/           # bbman subpackage (11 modules)
├── bbackup.py                # bbackup entry point
├── bbman.py                  # bbman entry point
├── config.yaml.example       # Annotated config template
├── pyproject.toml
└── uv.lock
```

---

## Documentation

| Doc | Description |
|:---|:---|
| [QUICKSTART.md](QUICKSTART.md) | Setup to first backup in 5 minutes |
| [INSTALL.md](INSTALL.md) | All installation methods |
| [docs/management.md](docs/management.md) | Full `bbman` reference |
| [docs/encryption.md](docs/encryption.md) | Encryption setup and key management |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](SECURITY.md) | How to report vulnerabilities |
| [SUPPORT.md](SUPPORT.md) | Where to ask questions or get help |
| [docs/cli-skills.md](docs/cli-skills.md) | Unified CLI skills catalog for humans and AI agents |
| [docs/VERSIONING.md](docs/VERSIONING.md) | Version source of truth, hook setup, and release validation |
| [docs/PUBLISHING_CHECKLIST.md](docs/PUBLISHING_CHECKLIST.md) | GitHub publishing and release readiness checklist |

---

## Roadmap

**Shipped**

- [x] Rich TUI with real-time transfer metrics
- [x] Incremental backups with rsync `--link-dest`
- [x] Backup rotation and retention policies
- [x] AES-256-GCM and RSA-4096 encryption
- [x] Full restore with optional rename
- [x] Filesystem backup for arbitrary host paths and directory trees
- [x] Management wrapper (`bbman`)
- [x] GitHub key integration for public key distribution
- [x] AI agent JSON I/O, skill discovery, `--dry-run`, and `--input-json` on all commands
- [x] Backup manifest verification with SHA-256 hashes
- [x] Temp-to-final upload promotion for local, SFTP, and rclone remotes

**Planned**

- [ ] Email and webhook notifications
- [ ] Cron-based scheduling integration
- [ ] Multi-server backup coordination
- [ ] Backup diff / comparison
- [ ] Web UI

---

## Credits

Built with [Rich](https://github.com/Textualize/rich), [Click](https://github.com/pallets/click), and [docker-py](https://github.com/docker/docker-py).

---

## License

[MIT](LICENSE)

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
