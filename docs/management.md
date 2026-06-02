# Management CLI (bbman)

> Reference for `bbman`, the companion command that handles setup, health, updates, and maintenance for bbackup.

---

## Overview

`bbman` is a separate entry point from `bbackup`. Where `bbackup` runs backups and restores, `bbman` handles everything around the application: first-time setup, dependency checks, update management, diagnostics, and cleanup. You can use it as a pre-flight wrapper for `bbackup` runs or independently for maintenance.

Every `bbman` command supports `--output json` for machine-readable output and `--input-json '{...}'` for single-object parameter passing. Set `BBACKUP_OUTPUT=json` to apply JSON mode globally to all subprocesses.

---

## Command reference

### `bbman setup`

Interactive first-time setup wizard. Run this before anything else.

```bash
bbman setup
bbman setup --no-interactive    # Skip wizard; return config state (agent mode)
bbman setup --output json       # JSON output
```

Checks Docker access, verifies `rsync` and `tar` are installed, installs any missing Python packages, and creates `~/.config/bbackup/config.yaml` if it does not exist. Optionally walks you through encryption key generation.

With `--no-interactive` (or `BBACKUP_NO_INTERACTIVE=1`), the wizard is skipped and the current config state is returned as JSON.

---

### `bbman health`

Comprehensive health check.

```bash
bbman health
bbman health --output json    # Machine-readable result
```

Checks:
- Docker daemon is running and your user has socket access
- System tools: `rsync`, `tar`, `rclone`
- Python dependencies match `pyproject.toml`
- Config file parses without errors
- Staging and log directories are writable

JSON output uses named fields (`{"ok": true, "message": "..."}`) rather than positional tuples, making it straightforward for agents to check individual components.

---

### `bbman check-deps`

Check (and optionally install) missing dependencies.

```bash
bbman check-deps              # Report only
bbman check-deps --install    # Install missing packages
bbman check-deps -i           # Shorthand
bbman check-deps --output json
```

On Ubuntu 22.04+ and Debian 12+ the system Python is externally managed (PEP 668). If you are not running inside a virtual environment, `--install` will print a warning and skip the install rather than failing with a pip error. Activate the bbackup venv first:

```bash
source ~/best-backup/.venv/bin/activate
bbman check-deps --install
```

---

### `bbman validate-config`

Parse and validate the config file.

```bash
bbman validate-config
bbman validate-config --output json
```

Reports YAML syntax errors, missing required fields, invalid paths, and unrecognized remote types. Shows a summary of what was parsed successfully.

---

### `bbman status`

Show backup history.

```bash
bbman status
bbman status --output json
```

Prints total backup count, combined size, how many are encrypted, and the most recent backup timestamps. In JSON mode, raw statistics are returned directly rather than a formatted display.

---

### `bbman cleanup`

Remove old staging files and logs.

```bash
bbman cleanup
bbman cleanup --staging-days 7    # Keep staging files newer than N days
bbman cleanup --log-days 30       # Keep log files newer than N days
bbman cleanup --yes               # Skip confirmation prompt
bbman cleanup --no-backups        # Do not touch old backup directories
bbman cleanup --no-temp           # Skip temporary file cleanup
bbman cleanup --yes --output json # Agent-friendly: skip prompt + JSON result
```

In JSON mode, confirmation is automatically skipped (equivalent to `--yes`).

---

### `bbman diagnostics`

Generate a diagnostic report.

```bash
bbman diagnostics
bbman diagnostics --report-file report.txt    # Save to file
bbman diagnostics --output json               # JSON output
```

Includes system info, Docker version, Python environment, config summary, and recent errors from the log file. Useful for bug reports.

Note: the save-to-file option is `--report-file` (not `--output`, which is reserved for the output format selector).

---

### `bbman check-updates`

Check whether the installed version is behind the configured repository.

```bash
bbman check-updates
bbman check-updates --branch main
bbman check-updates --output json
```

Uses SHA-256 checksums (Git-compatible) to compare local files against the remote tree. Reports which files have changed without downloading anything.

---

### `bbman update`

Pull updates from the repository.

```bash
bbman update
bbman update --method git       # Use git pull
bbman update --method download  # Download changed files directly
bbman update --yes              # Skip confirmation
bbman update --yes --output json
```

Creates a backup of the current installation before applying changes. Verifies checksums after updating. In JSON mode, confirmation is automatically skipped.

---

### `bbman repo-url`

Manage the repository URL used for update checks and downloads.

```bash
bbman repo-url                              # Show current URL and its source
bbman repo-url --url https://github.com/CruxExperts/best-backup
bbman repo-url --output json
```

The URL is resolved in this order:

1. `BBACKUP_REPO_URL` environment variable
2. `repo_url` in `~/.config/bbackup/management.yaml`
3. Default compiled into `bbman.py`

---

### `bbman run`

Launch `bbackup` through the wrapper.

```bash
bbman run backup --containers myapp
bbman run list-containers
bbman run restore --backup-path /path/to/backup --all
bbman run backup --containers myapp --output json   # JSON envelope wraps bbackup output
```

Arguments pass through directly to `bbackup`. With `--output json`, the subprocess output is captured and wrapped in the standard JSON envelope.

---

### `bbman skills`

Discover what `bbman` can do. Useful for AI agents performing progressive capability discovery.

```bash
bbman skills                     # Level-0: list all skill ids and summaries (JSON)
bbman skills setup               # Level-1: step-by-step guide + JSON schemas (JSON)
bbman skills maintenance
bbman skills updates
bbman skills dependencies
bbman skills --format markdown   # Full Markdown skills catalog (all commands)
```

Level-0 JSON output includes an `agent_hint` field pointing agents to the recommended env vars and `--input-json` usage.

---

## Agent integration

`bbman` is natively compatible with AI agents:

```bash
# Set globally once
export BBACKUP_OUTPUT=json
export BBACKUP_NO_INTERACTIVE=1

# Discover capabilities (JSON)
bbman skills

# Discover capabilities (Markdown)
bbman skills --format markdown

# Per-command skills docs
bbman health --skills

# Run with structured input/output
bbman health --output json
bbman cleanup --input-json '{"staging_days": 14, "yes": true}' --output json
bbman check-updates --output json
```

Every command returns the standard JSON envelope:

```json
{
  "schema_version": "1",
  "command": "health",
  "success": true,
  "data": { "docker": {"ok": true, "message": "..."}, "overall": "healthy" },
  "errors": []
}
```

See [README.md](../README.md#agent-integration) for exit code reference and the full envelope specification.

---

## Management config file

`~/.config/bbackup/management.yaml` controls wrapper behavior:

```yaml
repo_url: "https://github.com/CruxExperts/best-backup"
auto_check_updates: true
check_interval_days: 7
auto_setup_on_first_run: true
health_check_before_run: false
update_method: "git"           # git, download, or manual
```

---

## First-run detection

On first launch, `bbman` checks for `~/.config/bbackup/config.yaml` and `~/.local/share/bbackup/.first_run_complete`. If either is missing, the setup wizard runs automatically. You can also trigger it manually at any time with `bbman setup`.

---

## Common workflows

### Initial setup

```bash
bbman setup
bbman health
bbman check-deps --install
bbman validate-config
```

### Before a backup run

```bash
bbman health
bbman run backup --backup-set production --no-interactive
```

### Maintenance

```bash
bbman status
bbman cleanup --yes
bbman diagnostics --report-file diagnostics.txt
```

### Update cycle

```bash
bbman check-updates
bbman update --yes
bbman health
```

### Agent-driven workflow

```bash
export BBACKUP_OUTPUT=json BBACKUP_NO_INTERACTIVE=1
bbman skills                          # discover capabilities
bbman health --output json            # preflight check
bbman run backup --containers myapp --no-interactive --output json
bbman status --output json
bbman cleanup --yes --output json
```

---

## Troubleshooting

**Setup wizard does not appear automatically**

Run it directly: `bbman setup`

**Update fails**

```bash
bbman repo-url                               # Confirm URL is correct
bbman diagnostics --report-file report.txt  # Check for errors
cat ~/.local/share/bbackup/bbackup.log      # Review recent log entries
```

**Health check failures**

| Symptom | Fix |
|---|---|
| Docker not accessible | `sudo usermod -aG docker $USER && newgrp docker` |
| Missing Python packages | Activate the venv first, then `bbman check-deps --install` |
| Config parse error | `bbman validate-config` for details |
| rsync not found | `sudo apt-get install rsync` |

---

Back to [README.md](../README.md).

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
