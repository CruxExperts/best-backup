# CLI skills catalog

> Generated from the bbackup/bbman CLI metadata. Version: 1.8.0. This catalog is authoritative for this version.

## bbackup

### bbackup backup

**Summary**: Create Docker and/or filesystem backup.

Back up one or more Docker containers and optional filesystem paths. Supports incremental rsync (--link-dest), multiple remotes, and non-interactive JSON-driven operation.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--containers` | `string[]` | no | `` | Container names to back up (repeatable). |
| `--backup-set` | `string` | no | `` | Named backup set from config.yaml. |
| `--config-only` | `bool` | no | `False` | Back up only container configs (no volumes). |
| `--volumes-only` | `bool` | no | `False` | Back up only volumes (no configs). |
| `--no-networks` | `bool` | no | `False` | Skip network backups. |
| `--incremental` | `bool` | no | `False` | Enable incremental backup via rsync --link-dest. |
| `--no-interactive` | `bool` | no | `False` | Disable TUI and prompts; required for agent use. |
| `--solid-archive/--no-solid-archive` | `bool` | no | `` | Create a single compressed tarball for upload (overrides config backup.solid_archive). Use --no-solid-archive to disable. |
| `--remote` | `string[]` | no | `` | Remote storage destinations (repeatable). |
| `--paths` | `string[]` | no | `` | Filesystem paths to back up (repeatable). |
| `--exclude` | `string[]` | no | `` | Exclude patterns for filesystem backup (repeatable). |
| `--filesystem-set` | `string` | no | `` | Named filesystem backup set from config.yaml. |
| `--dry-run` | `bool` | no | `False` | Resolve targets and return a plan without executing. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Backup specific containers non-interactively with JSON output.

  ```bash
  bbackup backup --containers myapp --no-interactive --output json
  ```

- Incremental backup of a named backup set to a remote.

  ```bash
  bbackup backup --backup-set production --incremental --remote gdrive --no-interactive --output json
  ```

- JSON-driven backup of two containers.

  ```bash
  bbackup backup --input-json '{"containers":["myapp","mydb"],"incremental":true,"no_interactive":true}' --output json
  ```

  ```bash
  bbackup backup --input-json '{"containers":["myapp","mydb"],"incremental":true,"no_interactive":true,"output":"json"}' --output json
  ```

- Dry-run to see what would be backed up.

  ```bash
  bbackup backup --backup-set production --dry-run --no-interactive --output json
  ```

  ```bash
  bbackup backup --input-json '{"backup_set":"production","dry_run":true,"no_interactive":true,"output":"json"}' --output json
  ```

### bbackup init-config

**Summary**: Initialize configuration file from the bundled example template.

Create an example config.yaml in ~/.config/bbackup/ from the bundled template.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Initialize a starter config file.

  ```bash
  bbackup init-config --output json
  ```

  ```bash
  bbackup init-config --input-json '{"output":"json"}' --output json
  ```

### bbackup init-encryption

**Summary**: Initialize encryption keys for backup at-rest protection.

Generate symmetric and/or asymmetric keys for encrypting backups at rest and return a config snippet.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--method` | `string` | no | `'symmetric'` | Encryption method to use. |
| `--key-path` | `path` | no | `` | Directory to save key(s) (default: ~/.config/bbackup/). |
| `--password` | `string` | no | `` | Not currently supported for generated keys; command fails if provided. |
| `--algorithm` | `string` | no | `'rsa-4096'` | Algorithm for asymmetric keys. |
| `--upload-github` | `bool` | no | `False` | Remind about uploading public key to GitHub. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Generate asymmetric keys with JSON output.

  ```bash
  bbackup init-encryption --method asymmetric --algorithm rsa-4096 --output json
  ```

  ```bash
  bbackup init-encryption --input-json '{"method":"asymmetric","algorithm":"rsa-4096","output":"json"}' --output json
  ```

### bbackup list-backup-sets

**Summary**: List available backup sets.

List named backup sets from config with containers and scope.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- List backup sets with JSON output.

  ```bash
  bbackup list-backup-sets --output json
  ```

  ```bash
  bbackup list-backup-sets --input-json '{"output":"json"}' --output json
  ```

### bbackup list-backups

**Summary**: List available local backups.

List local backup directories in the staging directory or a specified location.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--backup-dir` | `path` | no | `` | Backup directory to list (default: staging directory). |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- List local backups with JSON output.

  ```bash
  bbackup list-backups --output json
  ```

  ```bash
  bbackup list-backups --input-json '{"output":"json"}' --output json
  ```

### bbackup list-containers

**Summary**: List all Docker containers.

List Docker containers with id, name, status, and image for inspection or backup planning.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- List all containers with JSON details.

  ```bash
  bbackup list-containers --output json
  ```

  ```bash
  bbackup list-containers --input-json '{"output":"json"}' --output json
  ```

### bbackup list-filesystem-sets

**Summary**: List configured filesystem backup sets.

List filesystem backup sets defined in config with targets and excludes.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- List filesystem backup sets with JSON output.

  ```bash
  bbackup list-filesystem-sets --output json
  ```

  ```bash
  bbackup list-filesystem-sets --input-json '{"output":"json"}' --output json
  ```

### bbackup list-remote-backups

**Summary**: List backups stored on a configured remote.

List available backups on a configured remote storage destination.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--remote` | `string` | yes | `` | Remote storage name to list backups from. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- List remote backups on a given remote.

  ```bash
  bbackup list-remote-backups --remote gdrive --output json
  ```

  ```bash
  bbackup list-remote-backups --input-json '{"remote":"gdrive","output":"json"}' --output json
  ```

### bbackup restore

**Summary**: Restore containers, volumes, networks, or filesystem paths from a backup.

Restore Docker resources and filesystem targets from a backup directory. Supports full restores, targeted restores, rename mappings, and dry-run mode.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--backup-path` | `path` | yes | `` | Path to the backup directory. |
| `--all` | `bool` | no | `False` | Restore all items from the backup. |
| `--containers` | `string[]` | no | `` | Specific container names to restore (repeatable). |
| `--volumes` | `string[]` | no | `` | Specific volume names to restore (repeatable). |
| `--networks` | `string[]` | no | `` | Specific network names to restore (repeatable). |
| `--filesystem` | `string[]` | no | `` | Filesystem target names to restore (repeatable). |
| `--filesystem-destination` | `path` | no | `` | Destination path for filesystem restore. |
| `--rename` | `string[]` | no | `` | Rename mappings in old:new format (repeatable). |
| `--dry-run` | `bool` | no | `False` | Return a restore plan without executing. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Restore everything from a backup directory.

  ```bash
  bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --output json
  ```

- Restore a single container from a backup using JSON input.

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"]}' --output json
  ```

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"],"output":"json"}' --output json
  ```

- Dry-run restore to inspect what would be restored.

  ```bash
  bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --dry-run --output json
  ```

  ```bash
  bbackup restore --input-json '{"backup_path":"/tmp/bbackup/backup_20260227_120000","all":true,"dry_run":true,"output":"json"}' --output json
  ```

### bbackup skills

**Summary**: List available bbackup skills for AI agent discovery.

List or inspect bbackup skills in JSON or Markdown formats.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `skill_id` | `string` | no | `` | Optional skill id for detailed view. |
| `--format` | `string` | no | `'json'` | Output as JSON or Markdown skills catalog. |
| `--output` | `string` | no | `` | Output format for detailed skill view (text or json). |

#### Examples

- List all bbackup skills in JSON.

  ```bash
  bbackup skills
  ```

- Dump the full Markdown skills catalog.

  ```bash
  bbackup skills --format markdown
  ```

## bbman

### bbman check-deps

**Summary**: Check and optionally install missing dependencies.

Check required and optional system and Python dependencies, optionally installing missing ones.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--install` | `bool` | no | `False` | Install missing packages. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Check dependencies only.

  ```bash
  bbman check-deps --output json
  ```

  ```bash
  bbman check-deps --input-json '{"output":"json"}' --output json
  ```

- Check and install missing dependencies.

  ```bash
  bbman check-deps --install --output json
  ```

  ```bash
  bbman check-deps --input-json '{"install":true,"output":"json"}' --output json
  ```

### bbman check-updates

**Summary**: Check for updates (file-level comparison with checksums).

Check whether the installed version is behind the configured repository.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--branch` | `string` | no | `'main'` | Branch to check (default: main). |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Check for updates on main branch.

  ```bash
  bbman check-updates --output json
  ```

  ```bash
  bbman check-updates --input-json '{"output":"json"}' --output json
  ```

### bbman cleanup

**Summary**: Cleanup old files and backups.

Remove old staging, log, backup, and temp files according to retention parameters.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--staging-days` | `int` | no | `7` | Keep staging files newer than N days (default 7). |
| `--log-days` | `int` | no | `30` | Keep log files newer than N days (default 30). |
| `--no-backups` | `bool` | no | `False` | Do not cleanup old backups. |
| `--no-temp` | `bool` | no | `False` | Do not cleanup temporary files. |
| `--yes` | `bool` | no | `False` | Skip confirmation prompt. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Cleanup with default retention settings and JSON output.

  ```bash
  bbman cleanup --yes --output json
  ```

  ```bash
  bbman cleanup --input-json '{"yes":true,"output":"json"}' --output json
  ```

### bbman diagnostics

**Summary**: Run diagnostics and optionally save report to file.

Run diagnostics and optionally save a detailed report to file for troubleshooting.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--report-file` | `path` | no | `` | Save diagnostics report to this file path. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Run diagnostics and return JSON summary.

  ```bash
  bbman diagnostics --output json
  ```

  ```bash
  bbman diagnostics --input-json '{"output":"json"}' --output json
  ```

### bbman health

**Summary**: Run comprehensive health check (Docker, rsync, rclone, Python packages).

Check Docker connectivity, system tools, Python dependencies, and configuration health. Designed for both human and agent consumption.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Run health check with JSON result.

  ```bash
  bbman health --output json
  ```

  ```bash
  bbman health --input-json '{"output":"json"}' --output json
  ```

### bbman repo-url

**Summary**: Show or set the repository URL override.

Show or update the repository URL used for update checks and downloads.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--url` | `string` | no | `` | Set repository URL override. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Show current repository URL in JSON.

  ```bash
  bbman repo-url --output json
  ```

  ```bash
  bbman repo-url --input-json '{"output":"json"}' --output json
  ```

### bbman run

**Summary**: Run bbackup commands through the bbman wrapper.

Launch the main bbackup CLI through bbman, preserving JSON envelope behavior when requested.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `command` | `string[]` | no | `` | The bbackup command and arguments to run. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### Examples

- Run a backup through bbman with JSON output.

  ```bash
  bbman run backup --containers myapp --no-interactive --output json
  ```

### bbman setup

**Summary**: Run interactive setup wizard for first-time configuration.

Run the interactive setup wizard to create an initial config.yaml. In agent mode, use --no-interactive with BBACKUP_NO_INTERACTIVE=1 to query current state instead of running the wizard.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--no-interactive` | `bool` | no | `False` | Skip wizard; return current config state (agent mode). |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Run setup in non-interactive mode for an agent.

  ```bash
  bbman setup --no-interactive --output json
  ```

  ```bash
  bbman setup --input-json '{"no_interactive":true,"output":"json"}' --output json
  ```

### bbman skills

**Summary**: List available bbman skills for AI agent discovery.

List or inspect bbman skills in JSON or Markdown formats.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `skill_id` | `string` | no | `` | Optional skill id for detailed view. |
| `--format` | `string` | no | `'json'` | Output as JSON or Markdown skills catalog. |
| `--output` | `string` | no | `` | Output format for detailed skill view (text or json). |

#### Examples

- List all bbman skills in JSON.

  ```bash
  bbman skills
  ```

- Dump the full Markdown skills catalog.

  ```bash
  bbman skills --format markdown
  ```

### bbman status

**Summary**: Show backup status and history.

Show backup statistics and history, suitable for both humans and agents.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Show backup status with JSON output.

  ```bash
  bbman status --output json
  ```

  ```bash
  bbman status --input-json '{"output":"json"}' --output json
  ```

### bbman update

**Summary**: Update application files.

Update the local installation from the configured repository using git or download methods.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--branch` | `string` | no | `'main'` | Branch to update from (default: main). |
| `--method` | `string` | no | `'git'` | Update method (git or download). |
| `--yes` | `bool` | no | `False` | Skip confirmation prompt. |
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Update non-interactively using git.

  ```bash
  bbman update --yes --output json
  ```

  ```bash
  bbman update --input-json '{"yes":true,"output":"json"}' --output json
  ```

### bbman validate-config

**Summary**: Validate configuration file.

Validate config.yaml and report backup sets, remotes, and encryption status.

#### CLI parameters

| Name | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `--skills` | `bool` | no | `False` | Show skills documentation for this command and exit. |
| `--output` | `string` | no | `` | Output format: text or json. |

#### JSON / environment parameters

| Name | Kind | Type | Required | Default | Description |
|---|---|---|:---:|---|---|
| `input_json` | json | `object` | no | `` | Flat JSON object providing all parameters. |

#### Examples

- Validate configuration file with JSON output.

  ```bash
  bbman validate-config --output json
  ```

  ```bash
  bbman validate-config --input-json '{"output":"json"}' --output json
  ```
