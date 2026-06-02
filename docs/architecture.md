# Architecture

> Design decisions, module breakdown, and configuration internals for contributors and advanced users.

---

## Technology stack

| Component | Library / tool | Version |
|---|---|---|
| Language | Python | 3.12+ |
| CLI framework | Click | 8.1.7+ |
| Terminal UI | Rich | 13.7.0+ |
| Docker integration | docker-py SDK | 7.0.0+ |
| Config format | PyYAML | 6.0.1+ |
| SFTP | paramiko | 3.4.0+ |
| Encryption | cryptography | 41.0.0+ |
| HTTP (key fetching) | requests | 2.31.0+ |
| Volume backup | rsync | system |
| Cloud storage | rclone | optional |

---

## Backup strategy

The tool uses two separate mechanisms depending on what it is backing up.

**Volumes** go through rsync running inside a temporary Alpine container that mounts the target volume. This handles large datasets well and supports incremental mode via `--link-dest`, where unchanged files become hardlinks to the previous backup instead of copies.

**Metadata** (container configs, network configs, logs) goes through `tar` with configurable compression. These are small and benefit more from good compression than from rsync's delta algorithm.

The two strategies produce separate artifacts that are bundled into a timestamped backup directory before encryption and remote upload.

---

## Module responsibilities

### `bbackup/cli.py`

Click entry point for the `bbackup` command. Handles argument parsing and delegates to the appropriate class. Commands: `backup`, `restore`, `list-containers`, `list-backup-sets`, `list-backups`, `list-remote-backups`, `list-filesystem-sets`, `init-config`, `init-encryption`, `skills`.

Every command accepts `--output [text|json]`, `--input-json JSON`, and `backup`/`restore` also accept `--dry-run`. In JSON mode the command emits the standard envelope to stdout; all diagnostic text goes to stderr. The `BBACKUP_OUTPUT` and `BBACKUP_NO_INTERACTIVE` env vars apply globally.

### `bbackup/cli_utils.py`

Shared foundation for the AI-agent-friendly JSON I/O layer. Contains:

- `output_option`, `input_json_option`, `dry_run_option` -- Click decorators applied to every command.
- `merge_json_input(ctx, json_str)` -- parses `--input-json` and overwrites matching `ctx.params` keys.
- `render_output(data, fmt, command, ...)` -- writes the standard JSON envelope to stdout when `fmt == "json"`.
- `json_error(command, message, exit_code, fmt)` -- emits an error envelope (JSON mode) or stderr line (text mode) then exits.
- `flatten_health_tuples(raw)` -- converts `Tuple[bool, str]` / `Tuple[bool, List, List]` values to named dicts for JSON consumers.
- Exit constants: `EXIT_SUCCESS=0`, `EXIT_USER_ERROR=1`, `EXIT_CONFIG_ERROR=2`, `EXIT_SYSTEM_ERROR=3`, `EXIT_PARTIAL=4`, `EXIT_CANCELLED=5`.
- Env var names: `BBACKUP_OUTPUT_ENV`, `BBACKUP_NO_INTERACTIVE_ENV`.

### `bbackup/skills.py`

Static skill descriptors for AI agent capability discovery. Contains `BBACKUP_SKILLS` and `BBMAN_SKILLS` dicts keyed by skill id, and `get_skill(cli, skill_id)` accessor.

Each skill entry includes: `id`, `summary`, `workflow` (ordered command list), `steps` (each with `command`, `description`, `optional_flags`, `valid_values`, `input_json_schema`), `examples`, `output_format`, `exit_codes`.

`get_skill(cli, None)` returns a level-0 overview with `agent_hint` and a compact skills list (80-90% token savings vs loading full `--help` trees). `get_skill(cli, skill_id)` returns the full step-by-step descriptor.

### JSON envelope contract

All commands emit exactly one JSON object to **stdout** in JSON mode:

```json
{
  "schema_version": "1",
  "command": "backup",
  "success": true,
  "data": { "...command-specific fields..." },
  "errors": []
}
```

`schema_version` bumps only on breaking field removals or renames; additive fields are always backward-compatible. All diagnostic and progress text is routed to **stderr** so stdout can be parsed unambiguously.

### `bbackup/config.py`

Loads and validates the YAML config file. Discovers config location using the priority chain below. Contains all dataclasses: `BackupScope`, `BackupSet`, `RemoteStorage`, `RetentionPolicy`, `IncrementalSettings`, `EncryptionSettings`, `Config`. CLI overrides are merged on top of file defaults.

### `bbackup/docker_backup.py`

Talks to the Docker API. Starts temporary Alpine containers, mounts target volumes, and runs rsync or tar inside them. Also inspects container and network configs. All Docker API errors are caught and reported via `BackupStatus`.

### `bbackup/backup_runner.py`

Orchestrates the full backup workflow:

```
init → select items → prepare staging dir
  → backup configs → backup volumes → backup networks
  → backup filesystem paths (if filesystem_targets provided)
  → [if solid_archive] create_solid_archive → optionally encrypt whole file → upload file → cleanup staging only after success
  → [else] encrypt dir (if enabled) → upload dir to remotes
  → rotate old backups
  → report
```

Reads and writes `BackupStatus` throughout so the TUI stays current.

### `bbackup/filesystem_backup.py`

Backs up arbitrary host filesystem paths and directory trees using rsync directly (no Docker). Key behaviors:

- Source path is rsynced to `backup_dir/filesystems/<target_name>/`
- Exclude patterns are written to a temp file and passed via `--exclude-from`; the temp file is always deleted in a `finally` block regardless of success or failure
- Incremental mode uses `--link-dest` pointing at the most recent previous `backup_YYYYMMDD_HHMMSS` sibling directory that contains the same target name. The current run directory is always excluded from the scan so a backup never links to itself
- Progress output is streamed line-by-line to the caller's callback for live TUI updates

### `bbackup/archive.py`

Solid-archive support: creates a single compressed tarball from a backup directory and optionally encrypts the whole file. Exposes `create_solid_archive()`, `unpack_solid_archive()`, and naming helpers `is_solid_archive_name()`, `strip_solid_archive_suffix()` used by list/rotation/restore. When solid archive is enabled, the backup flow tars the staging dir, compresses it (using `backup.compression`), and optionally encrypts the result so remotes receive one file. Staging cleanup runs only after at least one successful upload.

### `bbackup/restore.py`

Reads a backup directory or a solid archive file and restores containers, volumes, networks, and filesystem paths. When the backup path is a file (e.g. `.tar.gz` or `.tar.gz.enc`), unpacks to a temp dir, runs the same restore logic, then removes the temp dir. Supports renaming on restore (`--rename old:new`). Handles decryption (per-dir or whole-archive for solid archives) before restore.

### `bbackup/tui.py`

Two main classes:

- `BackupStatus`: thread-safe state object (lock-protected). Tracks current action, per-item status, errors, pause/cancel flags, transfer metrics.
- `BackupTUI`: the live dashboard. Renders a BTOP-style layout at 4 fps using Rich's `Live`. Handles keyboard input (Q, P, S, H). Also provides interactive selection dialogs for containers, backup sets, and scope options.

### `bbackup/remote.py`

Abstracts three upload targets behind a common interface: local filesystem (shutil), rclone (subprocess), and SFTP (paramiko). Each remote is tried independently so one failure does not abort others. Upload progress feeds into `BackupStatus`.

### `bbackup/rotation.py`

Applies daily/weekly/monthly retention. Calculates which backups to keep and removes the rest, oldest-first. Also checks storage quota thresholds and triggers cleanup when the limit is approached.

### `bbackup/encryption.py`

Two encryption modes:

- **Symmetric**: AES-256-GCM with a per-file random IV. One key encrypts and decrypts.
- **Asymmetric**: RSA-OAEP wrapping an AES session key. The public key encrypts, the private key decrypts.

Public keys can be referenced by path, URL, or GitHub shortcut (`github:USER/gist:ID`). Fetched keys are cached at `~/.cache/bbackup/keys/` with mode 600.

### `bbackup/logging.py`

`get_logger(name)` returns a properly named logger for any module. `setup_logging(config)` configures a `RotatingFileHandler` at `~/.local/share/bbackup/bbackup.log` on startup.

### `bbackup/management/`

11-module subpackage powering the `bbman` command. Each module handles one lifecycle concern:

| Module | Responsibility |
|---|---|
| `first_run.py` | Detect first run, locate config path |
| `setup_wizard.py` | Interactive first-time setup; delegates package installs to `dependencies.py` |
| `health.py` | Docker, system tool, config health checks |
| `diagnostics.py` | Generate diagnostic report |
| `dependencies.py` | Check and install missing packages; `is_venv()` guard prevents pip from running on an externally-managed system Python (PEP 668) |
| `updater.py` | Self-update from remote repo |
| `version.py` | Version detection, Git-compatible checksums |
| `repo.py` | Manage update source URL |
| `config.py` | Management-layer config (separate from backup config) |
| `status.py` | Backup history and totals |
| `cleanup.py` | Staging dir and log cleanup |
| `utils.py` | Shared utilities |

### `bbackup/cli_metadata.py`

Structured metadata registry describing all `bbackup` and `bbman` commands, parameters, JSON fields, and examples. Drives the JSON skills output, the generated `docs/cli-skills.md` catalog, and future tooling.

---

## Configuration system

### Discovery order

1. `~/.config/bbackup/config.yaml`
2. `~/.bbackup/config.yaml`
3. `/etc/bbackup/config.yaml`
4. `./config.yaml`

### Override chain

Config file provides defaults. CLI arguments override them at runtime. Interactive selection (when `--interactive` is active, which is the default) allows further runtime changes before the backup starts.

### Configuration sections

| Section | Purpose |
|---|---|
| `backup` | Staging dir, backup sets, default scope |
| `remotes` | Remote storage destinations |
| `rclone` | Optional default `transfers`/`checkers` for all rclone remotes |
| `retention` | Daily/weekly/monthly counts, quota |
| `incremental` | Enable rsync `--link-dest` mode |
| `logging` | Log path, level, rotation |
| `encryption` | Method, key paths, algorithm |
| `docker` | Socket path, timeout |

### Rclone options

For remotes with `type: rclone`, you can tune transfer concurrency so uploads use bandwidth more effectively. Options apply to all rclone operations (upload, list, size, purge) for that remote.

- **Per-remote:** Under the remote, set optional `rclone_options` with `transfers` (parallel file transfers) and `checkers` (parallel checkers for listing). Both are integers from 1 to 32; recommended defaults are 8 and 8.
- **Global default:** Top-level `rclone.default_options` sets defaults for all rclone remotes; per-remote `rclone_options` overrides it.
- **Omitted:** If neither is set, bbackup uses transfers=8 and checkers=8.

---

## BackupStatus data flow

`BackupStatus` is the shared state object between the backup worker thread and the TUI render thread. The worker calls `status.update()`, `status.add_error()`, and updates per-item dicts. The TUI reads these on every render cycle (4 fps). A `threading.Lock` protects all writes.

---

## Known gaps

- `create_metadata_archive()` exists in `docker_backup.py` but is not yet called from `backup_runner.py`. The method produces a compressed tar of config and network metadata. Wiring it in requires adding a call after all item backups complete and before `encrypt_backup_directory()`.
- S and H keyboard shortcuts print to console rather than opening a modal overlay. Modal implementation is planned.

---

## Repository structure

```
best-backup/
├── bbackup/                # Main package
│   ├── cli.py
│   ├── config.py
│   ├── docker_backup.py
│   ├── filesystem_backup.py
│   ├── backup_runner.py
│   ├── restore.py
│   ├── tui.py
│   ├── remote.py
│   ├── rotation.py
│   ├── encryption.py
│   ├── logging.py
│   ├── bbman_entry.py
│   └── management/         # bbman subpackage
├── docs/                   # Reference documentation
│   ├── architecture.md     # This file
│   ├── management.md       # bbman reference
│   ├── encryption.md       # Encryption guide
│   └── dev/               # Internal dev notes and test logs
├── scripts/                # Test and utility scripts
├── bbackup.py              # bbackup entry point
├── bbman.py                # bbman entry point
├── config.yaml.example
├── pyproject.toml
└── uv.lock
```

---

Back to [README.md](../README.md).

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
