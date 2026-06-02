# Quick start guide

> Get from zero to a completed backup in about 5 minutes.

---

## Step 1: Install

`uv` handles the isolated tool environment automatically and wires `bbackup` and `bbman` into your PATH.

**Single user** (commands available only to you):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool update-shell
```

Open a new shell, then:

```bash
uv tool install git+https://github.com/CruxExperts/best-backup.git
```

**Server / all users** (commands available to every user and cron jobs):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo env UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/usr/local/bin uv tool install git+https://github.com/CruxExperts/best-backup.git
```

If you already have `bbackup` installed via `uv` and only need to update it, run `uv tool upgrade bbackup` for a single-user install or `sudo env UV_TOOL_DIR=/opt/uv/tools UV_TOOL_BIN_DIR=/usr/local/bin uv tool upgrade bbackup` for the server-wide method, rather than re-running `uv tool install`. See [INSTALL.md](INSTALL.md) for uninstall and alternative install methods.

---

## Step 2: First-time setup

```bash
bbman setup
```

The setup wizard checks Docker access, verifies system dependencies (`rsync`, `tar`), installs any missing Python packages, and creates a starter config at `~/.config/bbackup/config.yaml`.

If you prefer to do this manually:

```bash
bbackup init-config
```

For agent or CI use, skip the wizard:

```bash
bbman setup --no-interactive --output json
```

---

## Step 3: Edit your config

Open `~/.config/bbackup/config.yaml` and define which containers you want to back up and where to store the results.

```yaml
backup:
  local_staging: /tmp/bbackup_staging
  backup_sets:
    production:
      description: "Production stack"
      containers:
        - myapp
        - mydb
      scope:
        volumes: true
        configs: true

remotes:
  local:
    enabled: true
    type: local
    path: ~/backups/docker
```

A fully annotated example with all options is in [`config.yaml.example`](config.yaml.example).

---

## Step 4: Run your first backup

```bash
bbackup backup
```

You'll get an interactive container picker, then a live dashboard showing transfer speed, bytes moved, and per-container status as the backup runs.

To skip the picker and go straight to a specific set:

```bash
bbackup backup --backup-set production
```

Or target individual containers directly:

```bash
bbackup backup --containers myapp mydb
```

---

## Common scenarios

### Backup only configs (no volume data)

```bash
bbackup backup --config-only
```

### Incremental backup (only changed data)

```bash
bbackup backup --incremental
```

Uses rsync `--link-dest` so unchanged files are hardlinked from the previous backup rather than copied. Works well for large volumes that change slowly.

### Send to Google Drive

1. Configure rclone first:
   ```bash
   rclone config
   # Create a remote named "gdrive"
   ```

2. Add to your config:
   ```yaml
   remotes:
     gdrive:
       enabled: true
       type: rclone
       remote_name: gdrive
       path: /backups/docker
   ```

3. Run:
   ```bash
   bbackup backup --remote gdrive
   ```

### Back up local filesystem paths

Point `--paths` at any directory or file. Everything inside is backed up recursively, and you can exclude patterns the same way `.gitignore` works:

```bash
bbackup backup --paths /home/user/documents /srv/data
bbackup backup --paths /home/user/documents --exclude "*.tmp" --exclude ".cache/"
```

Or define named sets in your config and reference them by name:

```yaml
filesystem:
  home-data:
    targets:
      - name: documents
        path: /home/user/Documents
        excludes: ["*.tmp", ".cache/", "node_modules/"]
```

```bash
bbackup backup --filesystem-set home-data
```

Filesystem backups go through the same encryption, remote upload, and rotation pipeline as Docker backups.

### Restore a filesystem backup

```bash
bbackup restore --backup-path ~/backups/docker/backup_2026-02-26 \
  --filesystem documents \
  --filesystem-destination /home/user/documents
```

### Restore from a backup

```bash
bbackup restore --backup-path ~/backups/docker/backup_2026-02-26 --all
```

Restore specific containers only:

```bash
bbackup restore --backup-path ~/backups/docker/backup_2026-02-26 --containers myapp
```

---

## Troubleshooting

**"Permission denied" on Docker socket**

```bash
sudo usermod -aG docker $USER
newgrp docker
```

**`rsync` not found**

```bash
sudo apt-get install rsync      # Debian / Ubuntu
sudo yum install rsync          # RHEL / CentOS
```

**`rclone` not found**

```bash
curl https://rclone.org/install.sh | sudo bash
```

**Config not found**

```bash
bbackup init-config
# or
bbman setup
```

---

## Using with AI agents

Every command supports `--output json` for structured output and `--input-json '{...}'` for parameter passing. Set two env vars once and all subprocesses inherit them:

```bash
export BBACKUP_OUTPUT=json
export BBACKUP_NO_INTERACTIVE=1

# Discover capabilities
bbackup skills
bbman skills

# Run a non-interactive backup with JSON result
bbackup backup --containers myapp --no-interactive --output json

# Or via flat JSON input
bbackup backup --input-json '{"containers":["myapp"],"incremental":true,"no_interactive":true}' --output json
```

See [README.md](README.md#agent-integration) for the full agent integration reference including the envelope spec, exit codes, and skills protocol.

---

## Next steps

- [README.md](README.md) - Full CLI reference and feature list
- [INSTALL.md](INSTALL.md) - Alternative installation methods
- [docs/management.md](docs/management.md) - Full `bbman` reference
- [docs/encryption.md](docs/encryption.md) - Encryption setup
- [`config.yaml.example`](config.yaml.example) - All configuration options

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
