# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses [semantic versioning](https://semver.org/).

Historical entries preserve the install and packaging guidance that was current
for that release. Use `README.md`, `INSTALL.md`, and `docs/VERSIONING.md` for
current uv-based install, development, and release instructions.

---

## [Unreleased]

---

## [1.7.0] - 2026-03-06

### Added

- Solid archive mode: optional single compressed tarball (and optional whole-file encryption) before upload so remotes receive one file instead of many. Config `backup.solid_archive` and CLI `--solid-archive` / `--no-solid-archive`. Restore accepts a backup path that is a file: it unpacks to a temp dir, restores selected items, then cleans up. Listing and retention treat directories and archive files (e.g. `backup_*.tar.gz`, `backup_*.tar.gz.enc`) the same. Staging cleanup runs only after at least one successful upload. See `config.yaml.example` and [docs/architecture.md](docs/architecture.md).

---

## [1.6.0] - 2026-03-04

### Added

- Rclone transfer and concurrency options: config-driven `transfers` and `checkers` for all rclone operations (upload, list, size, purge). Per-remote optional `rclone_options` and optional top-level `rclone.default_options`; recommended defaults 8/8, cap 32. See `config.yaml.example` and [docs/architecture.md](docs/architecture.md#rclone-options).

---

## [1.5.0] - 2026-03-02

### Added

- `is_venv()` helper in `bbackup/management/dependencies.py`: detects whether the current Python is running inside a virtual environment by checking `sys.real_prefix` and `sys.base_prefix`
- PEP 668 guard in `install_python_packages()`: on Ubuntu 22.04+ and Debian 12+ (externally-managed system Python), the function now prints a clear activation message and returns `False` instead of letting pip fail with an unhelpful error
- `bbackup/cli_metadata.py`: unified metadata layer describing CLI commands, parameters, JSON fields, and examples for `bbackup` and `bbman`
- `scripts/generate_cli_skills.py`: generator for `docs/cli-skills.md` and `docs/cli-skills-index.json`, producing a versioned CLI skills catalog from metadata
- `docs/cli-skills.md`: agent-friendly, generated skills catalog for all core `bbackup`/`bbman` commands, with CLI + JSON examples
- Per-command `--skills` flags on core `bbackup`/`bbman` commands to print their skills section from `docs/cli-skills.md`
- CI step in `.github/workflows/ci.yml` that runs `python scripts/generate_cli_skills.py --check` to ensure skills docs are up to date

### Changed

- `bbackup/management/setup_wizard.py`: the "Install missing packages?" branch now delegates to `install_python_packages()` from `dependencies.py` instead of calling `subprocess.run(pip install ...)` directly, consolidating the venv check and error handling in one place
- `INSTALL.md`: pipx is now the recommended install method; dedicated PEP 668 troubleshooting section points users to pipx; manual venv install documented for development use
- `QUICKSTART.md` Step 1: installation example updated to use pipx, with a server-wide pipx variant for shared installs
- `README.md` installation section: updated to show pipx-based install for single user and server-wide setups, pointing to `INSTALL.md` for alternatives
- `README.md` and `docs/README.md`: link the new `docs/cli-skills.md` catalog from the documentation tables

---

## [1.4.0] - 2026-02-28

### Changed

- README overhauled: centered hero header, GitHub Alerts (`[!TIP]`), icon column in feature table, collapsible CLI sections via `<details>`, docs table, and install one-liner at top of page
- Version badge in README updated to reflect current release

---

## [1.3.3] - 2026-02-27

### Added

- AI-agent-friendly JSON I/O layer across all `bbackup` and `bbman` commands
- `--output [text|json]` on every command: emits a versioned JSON envelope to stdout; all diagnostic text goes to stderr
- `--input-json JSON` on every command: accepts all parameters as a single flat JSON object; merges over CLI flags; unknown keys silently ignored (forward-compatible)
- `--dry-run` on `bbackup backup` and `bbackup restore`: resolves targets and returns a plan without executing
- `bbackup skills` and `bbman skills` subcommands for progressive AI agent capability discovery; each skill includes step-by-step guidance and per-step `input_json_schema`
- `BBACKUP_OUTPUT=json` env var: sets JSON mode globally for all subprocesses without passing `--output json` to each command
- `BBACKUP_NO_INTERACTIVE=1` env var: suppresses TUI, prompts, and pagers system-wide
- `--no-interactive` flag on `bbman setup`: skip wizard and return config state as JSON (agent mode)
- `bbackup/cli_utils.py`: shared foundation module with decorators, envelope builder, `merge_json_input`, `json_error`, `flatten_health_tuples`, and semantic exit constants (0-5)
- `bbackup/skills.py`: static skill descriptors for 6 `bbackup` skills and 4 `bbman` skills with per-step `input_json_schema` (JSON Schema)
- 30 new tests in `tests/test_cli.py` across 6 classes: `TestJSONOutputMode`, `TestInputJSON`, `TestSkillsCommand`, `TestDryRun`, `TestEnvVars`, `TestExitCodes`
- Agent integration section in `README.md` with quickstart, envelope spec, env var table, exit code table, skills protocol, and dry-run example

### Changed

- `bbman diagnostics --output` (file path) renamed to `bbman diagnostics --report-file` to free `--output` for the universal format selector
- `bbman --version` now reports the actual package version from `bbackup.__version__` instead of the hardcoded `"1.0.0"`
- All `sys.exit(1)` calls replaced with semantic exit constants: `EXIT_USER_ERROR=1`, `EXIT_CONFIG_ERROR=2`, `EXIT_SYSTEM_ERROR=3`, `EXIT_PARTIAL=4`, `EXIT_CANCELLED=5`
- `bbman health` and `bbman check-deps` JSON output uses named sub-dicts (`{"ok": bool, "message": "..."}`) instead of positional tuples
- `bbackup list-containers` JSON output now includes the `"id"` field for each container
- `bbackup list-backup-sets` JSON output now includes the full `"scope"` dict per set
- Error output from pre-run validation (unknown backup set, missing path, etc.) routed to stderr in text mode and to the `errors` array in JSON mode; stdout is reserved for the JSON envelope only

### Fixed

- TUI no longer blocks agents: `--output json` or `BBACKUP_NO_INTERACTIVE=1` automatically bypasses `run_with_live_dashboard()`
- `backup` command now captures and uses the return value from `runner.run_backup()` for the JSON result payload
- `bbman status` in JSON mode returns structured data directly instead of returning `None`
- `bbman cleanup` JSON output uses `.get("kept", 0)` to guarantee a stable shape regardless of cleanup module version

---

## [1.3.2] - 2026-02-27

### Changed

- Documentation updates aligned with v1.3.0 and v1.3.1: README, INSTALL, QUICKSTART, docs/architecture.md, docs/management.md, docs/encryption.md updated to reflect filesystem backup, restore options, CLI changes, and project structure

---

## [1.3.1] - 2026-02-27

### Added

- 53 unit tests for filesystem backup and restore in `tests/test_filesystem_backup.py`, covering `FilesystemBackup`, `restore_filesystem_path`, `restore_backup` filesystem loop, and `BackupRunner` integration
- 7 real-rsync integration tests in `tests/integration/test_docker_integration.py`: basic backup, exclude patterns, incremental hardlinks, progress callback, and roundtrip restore
- `--yes` / `-y` flag on `maintenance/release.py` for non-interactive (agent/CI) execution

### Fixed

- `FilesystemBackup._build_rsync_cmd` was passing the current run directory as the staging directory to `_find_previous_backup`, causing incremental backups to use `--link-dest` pointing at themselves
- `_find_previous_backup` now accepts `current_run_dir` and excludes it from the candidate scan so a backup never links to itself

---

## [1.3.0] - 2026-02-26

### Added

- Filesystem backup: back up arbitrary host paths and directory trees with rsync, gitignore-style exclude patterns, and incremental `--link-dest` support
- New `bbackup/filesystem_backup.py` module with `FilesystemBackup` class
- `FilesystemTarget` and `FilesystemBackupSet` dataclasses in `config.py`
- `filesystems:` section in `config.yaml.example` with annotated examples
- `--paths`, `--exclude`, `--filesystem-set` options on `bbackup backup`
- `--filesystem`, `--filesystem-destination` options on `bbackup restore`
- `bbackup list-filesystem-sets` subcommand
- Filesystem panel in live TUI dashboard (third column alongside containers and volumes)

---

## [1.2.1] - 2026-02-26

### Changed

- Expanded test coverage from 59% to 76% across all core modules
- Resolved all ruff lint violations in the `bbackup` package

### Fixed

- `BackupRunner._parse_rsync_progress` hoisted from closure to method for reuse
- `BackupStatus.update()` no longer receives `transfer_speed` as a kwarg (set directly)

---

## [1.2.0] - 2026-02-26

### Added

- Full CI testing suite: 289 unit tests covering all `bbackup/` modules
- `scripts/run_tests.py` agentic sandbox test runner with Docker isolation and self-healing debug loop
- `Dockerfile.test` for sandboxed test execution
- `requirements-dev.txt` with pytest, pytest-cov, pytest-mock
- GitHub Actions CI workflow with unit and integration test jobs
- LICENSE file (MIT)
- CHANGELOG.md following Keep a Changelog format
- Community health files: CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue templates, PR template
- Project identity system: copyright footer stamped across all public-facing docs
- `maintenance/release.py` automated release workflow with doc validation
- `maintenance/check_docs.py` stale-doc detection with agent-driven auto-update support
- `maintenance/bump_version.py` conventional-commit version bumping

---

## [1.1.0] - 2026-02-26

### Added

- Rich TUI with BTOP-style live dashboard and real-time transfer metrics (speed, bytes, file count, ETA)
- Docker backup for containers, volumes, networks, and configuration metadata
- Incremental backups using rsync `--link-dest` (hardlinks unchanged files instead of copying)
- AES-256-GCM symmetric encryption at rest
- RSA-4096 / ECDSA P-384 asymmetric encryption with public/private key separation
- GitHub key hosting: reference public keys by `github:USERNAME/gist:ID` shortcut
- Remote storage: Google Drive via rclone, SFTP via paramiko, local directory
- Time-based backup rotation with daily/weekly/monthly retention and storage quota enforcement
- Full restore of containers, volumes, and networks with optional rename on restore
- Backup sets: named container groups defined in config for repeatable runs
- Selective backup: `--config-only`, `--volumes-only`, `--no-networks` flags
- `bbman` management CLI: setup wizard, health checks, dependency management, diagnostics, self-update
- Interactive container selection with TUI dialog
- Keyboard controls in TUI: Q (quit), P (pause/resume), S (skip), H (help)
- YAML configuration with priority chain and CLI override support
- Rotating file logger via `get_logger()` factory

### Changed

- Project structured for standalone GitHub distribution

---

[Unreleased]: https://github.com/CruxExperts/best-backup/compare/v1.7.0...HEAD
[1.7.0]: https://github.com/CruxExperts/best-backup/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/CruxExperts/best-backup/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/CruxExperts/best-backup/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/CruxExperts/best-backup/compare/v1.3.3...v1.4.0
[1.3.3]: https://github.com/CruxExperts/best-backup/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/CruxExperts/best-backup/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/CruxExperts/best-backup/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/CruxExperts/best-backup/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/CruxExperts/best-backup/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/CruxExperts/best-backup/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/CruxExperts/best-backup/releases/tag/v1.1.0

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
