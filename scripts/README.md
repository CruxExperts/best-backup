# Scripts

> Utility scripts for testing and development. Not required for normal use.

---

## Available scripts

### `create_sandbox.py`

Generates a test filesystem with 13,000+ files across realistic directory structures (archives, projects, documents, media). Useful for testing backup, restore, and incremental backup behavior without touching real data.

```bash
uv run python scripts/create_sandbox.py --output /tmp/bbackup_sandbox
uv run python scripts/create_sandbox.py --output /tmp/bbackup_sandbox --quick   # Fewer files, faster
uv run python scripts/create_sandbox.py --output /tmp/bbackup_sandbox --file-count 5000
```

Options:

| Flag | Description |
|---|---|
| `--output, -o` | Output directory (default: `/tmp/bbackup_sandbox`) |
| `--config, -c` | YAML config file for advanced options |
| `--file-count` | Target file count |
| `--size-mb` | Target total size in MB |
| `--harvest-system` | Include read-only copies of real system files |
| `--quick` | Reduced file count for faster runs |
| `--verbose, -v` | Verbose output |

---

### `test_sandbox_backups.py`

Runs backup scenarios against the sandbox created by `create_sandbox.py` and logs results.

```bash
uv run python scripts/test_sandbox_backups.py
```

---

### `populate_postgres.sh`

Populates a PostgreSQL test container with sample data for testing backup/restore with a live database.

```bash
./scripts/populate_postgres.sh
```

---

### `test_backup_with_locks.sh`

Tests backup behavior when the database has active locks, verifying that backups complete cleanly under concurrent write load.

```bash
./scripts/test_backup_with_locks.sh
```

---

### `get_github_key.sh`

Fetches SSH public keys from a GitHub user profile.

```bash
./scripts/get_github_key.sh YOUR_USERNAME
```

---

### `upload_key_to_github.sh`

Uploads an encryption public key to a GitHub Gist.

```bash
./scripts/upload_key_to_github.sh /path/to/backup_public.pem
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
