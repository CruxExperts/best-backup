"""
bbackup/skills.py
Purpose: Static skill descriptors for AI agent capability discovery.
         Each skill groups related CLI commands with step-by-step guidance,
         JSON schema for --input-json, and copy-paste examples.
         Consumed by the `bbackup skills` and `bbman skills` subcommands.
Created: 2026-02-27
Last Updated: 2026-02-27
"""

from typing import Dict, Any, Optional

# ---------------------------------------------------------------------------
# bbackup skill registry
# ---------------------------------------------------------------------------

BBACKUP_SKILLS: Dict[str, Any] = {
    "docker-backup": {
        "id": "docker-backup",
        "summary": "Back up Docker containers, volumes, networks, and configs.",
        "common": True,
        "workflow": ["list-containers", "backup"],
        "steps": [
            {
                "command": "bbackup list-containers --output json",
                "description": "Enumerate running containers to identify backup targets.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
            {
                "command": "bbackup backup --containers <name> --output json",
                "description": (
                    "Back up one or more containers. "
                    "Omit --containers to use a backup set or interactive selection."
                ),
                "required_flags": [],
                "optional_flags": {
                    "--containers": "container names (repeatable)",
                    "--backup-set": "named backup set from config",
                    "--incremental": "rsync --link-dest against previous backup",
                    "--remote": "remote storage name (repeatable)",
                    "--no-interactive": "disable TUI (required for agent use)",
                    "--dry-run": "resolve targets without executing",
                    "--output": "text or json",
                    "--input-json": "all params as flat JSON object",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "containers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Container names to back up.",
                        },
                        "backup_set": {
                            "type": "string",
                            "description": "Named backup set from config.yaml.",
                        },
                        "incremental": {
                            "type": "boolean",
                            "default": False,
                            "description": "Enable incremental backup via rsync --link-dest.",
                        },
                        "no_interactive": {
                            "type": "boolean",
                            "default": False,
                            "description": "Suppress TUI; required for non-interactive use.",
                        },
                        "remote": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Remote storage destination names.",
                        },
                        "config_only": {"type": "boolean", "default": False},
                        "volumes_only": {"type": "boolean", "default": False},
                        "no_networks": {"type": "boolean", "default": False},
                        "dry_run": {
                            "type": "boolean",
                            "default": False,
                            "description": "Return plan JSON without executing.",
                        },
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbackup backup --containers myapp --no-interactive --output json",
            "bbackup backup --backup-set production --incremental --no-interactive --output json",
            'bbackup backup --input-json \'{"containers":["myapp","mydb"],"incremental":true,"no_interactive":true}\' --output json',
            "bbackup backup --dry-run --output json",
        ],
        "output_format": (
            '{"backup_dir": "...", "containers": {"name": "success|failed"}, '
            '"volumes": {...}, "networks": {...}, "filesystems": {...}, "errors": []}'
        ),
        "exit_codes": {0: "success", 1: "user error", 2: "config error", 3: "system error", 4: "partial", 5: "cancelled"},
    },

    "filesystem-backup": {
        "id": "filesystem-backup",
        "summary": "Back up arbitrary host filesystem paths with gitignore-style excludes.",
        "common": True,
        "workflow": ["list-filesystem-sets", "backup"],
        "steps": [
            {
                "command": "bbackup list-filesystem-sets --output json",
                "description": "List configured filesystem backup sets.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbackup backup --paths <path> --exclude <pattern> --no-interactive --output json",
                "description": "Back up specific filesystem paths.",
                "required_flags": ["--paths"],
                "optional_flags": {
                    "--paths": "filesystem paths (repeatable)",
                    "--exclude": "exclude patterns, gitignore-style (repeatable)",
                    "--filesystem-set": "named set from config",
                    "--no-interactive": "required for agent use",
                    "--output": "text or json",
                    "--input-json": "all params as flat JSON object",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filesystem paths to back up.",
                        },
                        "exclude": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Patterns to exclude (gitignore-style).",
                        },
                        "filesystem_set": {"type": "string"},
                        "no_interactive": {"type": "boolean", "default": True},
                        "incremental": {"type": "boolean", "default": False},
                        "dry_run": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": ["paths"],
                },
            },
        ],
        "examples": [
            "bbackup backup --paths /home/user/documents --no-interactive --output json",
            'bbackup backup --input-json \'{"paths":["/home/user/docs"],"exclude":["*.tmp","node_modules/"],"no_interactive":true}\' --output json',
            "bbackup backup --filesystem-set home-data --no-interactive --output json",
        ],
        "output_format": (
            '{"backup_dir": "...", "filesystems": {"name": "success|failed"}, "errors": []}'
        ),
        "exit_codes": {0: "success", 1: "user error", 3: "system error", 4: "partial", 5: "cancelled"},
    },

    "restore": {
        "id": "restore",
        "summary": "Restore containers, volumes, networks, or filesystem paths from a backup.",
        "common": True,
        "workflow": ["list-backups", "restore"],
        "steps": [
            {
                "command": "bbackup list-backups --output json",
                "description": "List available local backups to find the target backup path.",
                "required_flags": [],
                "optional_flags": {
                    "--backup-dir": "staging directory to list (default: from config)",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "backup_dir": {"type": "string"},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
            {
                "command": "bbackup restore --backup-path <path> --all --output json",
                "description": "Restore from a backup directory.",
                "required_flags": ["--backup-path"],
                "optional_flags": {
                    "--backup-path": "path to the backup directory",
                    "--all": "restore all items from backup",
                    "--containers": "specific container names (repeatable)",
                    "--volumes": "specific volume names (repeatable)",
                    "--networks": "specific network names (repeatable)",
                    "--filesystem": "specific filesystem target names (repeatable)",
                    "--filesystem-destination": "destination path for filesystem restore",
                    "--rename": "rename mapping old:new (repeatable)",
                    "--dry-run": "show what would be restored",
                    "--output": "text or json",
                    "--input-json": "all params as flat JSON object",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "backup_path": {
                            "type": "string",
                            "description": "Absolute path to the backup directory.",
                        },
                        "all": {"type": "boolean", "default": False},
                        "containers": {"type": "array", "items": {"type": "string"}},
                        "volumes": {"type": "array", "items": {"type": "string"}},
                        "networks": {"type": "array", "items": {"type": "string"}},
                        "filesystem": {"type": "array", "items": {"type": "string"}},
                        "filesystem_destination": {"type": "string"},
                        "rename": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Rename mappings in old:new format.",
                        },
                        "dry_run": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": ["backup_path"],
                },
            },
        ],
        "examples": [
            "bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --all --output json",
            'bbackup restore --input-json \'{"backup_path":"/tmp/bbackup/backup_20260227_120000","containers":["myapp"]}\' --output json',
            "bbackup restore --backup-path /tmp/bbackup/backup_20260227_120000 --dry-run --output json",
        ],
        "output_format": (
            '{"containers": {"name": "success|failed"}, "volumes": {...}, '
            '"networks": {...}, "filesystems": {...}, "errors": []}'
        ),
        "exit_codes": {0: "success", 1: "user error", 3: "system error", 4: "partial"},
    },

    "inspect": {
        "id": "inspect",
        "summary": "Inspect available containers, backup sets, filesystem sets, and local backups.",
        "common": True,
        "workflow": ["list-containers", "list-backup-sets", "list-filesystem-sets", "list-backups"],
        "steps": [
            {
                "command": "bbackup list-containers --output json",
                "description": "List Docker containers with id, name, status, image.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbackup list-backup-sets --output json",
                "description": "List named backup sets with containers and scope.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbackup list-filesystem-sets --output json",
                "description": "List filesystem backup sets with targets and excludes.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbackup list-backups --output json",
                "description": "List local backup directories.",
                "required_flags": [],
                "optional_flags": {
                    "--backup-dir": "directory to list",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "backup_dir": {"type": "string"},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbackup list-containers --output json",
            "bbackup list-backup-sets --output json",
            "bbackup list-backups --output json",
        ],
        "output_format": "Varies by command; all include top-level array + schema_version envelope.",
        "exit_codes": {0: "success", 2: "config error", 3: "system error"},
    },

    "encryption": {
        "id": "encryption",
        "summary": "Generate encryption keys for backup at-rest protection.",
        "common": False,
        "workflow": ["init-encryption"],
        "steps": [
            {
                "command": "bbackup init-encryption --method asymmetric --output json",
                "description": "Generate RSA-4096 key material. Returns key paths and config snippet.",
                "required_flags": [],
                "optional_flags": {
                    "--method": "symmetric, asymmetric, or both",
                    "--key-path": "directory to save keys (default: ~/.config/bbackup/)",
                    "--algorithm": "rsa-4096",
                    "--output": "text or json",
                    "--input-json": "all params as flat JSON object",
                },
                "valid_values": {
                    "--method": ["symmetric", "asymmetric", "both"],
                    "--algorithm": ["rsa-4096"],
                    "--output": ["text", "json"],
                },
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["symmetric", "asymmetric", "both"],
                            "default": "symmetric",
                        },
                        "key_path": {"type": "string"},
                        "algorithm": {
                            "type": "string",
                            "enum": ["rsa-4096"],
                            "default": "rsa-4096",
                        },
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbackup init-encryption --method asymmetric --output json",
            'bbackup init-encryption --input-json \'{"method":"asymmetric","algorithm":"rsa-4096"}\' --output json',
        ],
        "output_format": (
            '{"method": "...", "key_paths": {"public": "...", "private": "..."}, '
            '"config_snippet": "...", "success": true}'
        ),
        "exit_codes": {0: "success", 1: "user error", 3: "system error"},
    },

    "remote-storage": {
        "id": "remote-storage",
        "summary": "List backups stored on remote storage destinations.",
        "common": False,
        "workflow": ["list-remote-backups"],
        "steps": [
            {
                "command": "bbackup list-remote-backups --remote <name> --output json",
                "description": "List backups available on a configured remote.",
                "required_flags": ["--remote"],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "remote": {"type": "string", "description": "Remote storage name from config."},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": ["remote"],
                },
            },
        ],
        "examples": [
            "bbackup list-remote-backups --remote gdrive --output json",
        ],
        "output_format": '{"remote": "gdrive", "backups": [{"name": "...", "remote_path": "..."}]}',
        "exit_codes": {0: "success", 1: "user error", 2: "config error", 3: "system error"},
    },
}

# ---------------------------------------------------------------------------
# bbman skill registry
# ---------------------------------------------------------------------------

BBMAN_SKILLS: Dict[str, Any] = {
    "setup": {
        "id": "setup",
        "summary": "First-time setup, config validation, and system health check.",
        "common": True,
        "workflow": ["setup", "validate-config", "health"],
        "steps": [
            {
                "command": "bbman setup --no-interactive --output json",
                "description": (
                    "Run setup. With --no-interactive the wizard is skipped; "
                    "returns current config state without prompts."
                ),
                "required_flags": [],
                "optional_flags": {
                    "--no-interactive": "skip wizard (agent mode)",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "no_interactive": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
            {
                "command": "bbman validate-config --output json",
                "description": "Validate config.yaml and report backup sets, remotes, and encryption status.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbman health --output json",
                "description": "Run comprehensive health check: Docker, rsync, rclone, Python packages.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbman health --output json",
            "bbman validate-config --output json",
            "bbman setup --no-interactive --output json",
        ],
        "output_format": (
            '{"docker": {"ok": true, "message": "..."}, "rsync": {...}, '
            '"python_packages": {"ok": true, "installed": [...], "missing": []}, '
            '"overall": "healthy", "all_critical_ok": true}'
        ),
        "exit_codes": {0: "all critical ok", 1: "critical dependency missing", 3: "system error"},
    },

    "maintenance": {
        "id": "maintenance",
        "summary": "Cleanup old files, check status, and run diagnostics.",
        "common": True,
        "workflow": ["status", "cleanup", "diagnostics"],
        "steps": [
            {
                "command": "bbman status --output json",
                "description": "Show backup statistics and history.",
                "required_flags": [],
                "optional_flags": {"--output": "text or json"},
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {"output": {"type": "string", "enum": ["text", "json"]}},
                    "required": [],
                },
            },
            {
                "command": "bbman cleanup --yes --output json",
                "description": "Remove old staging, log, and backup files.",
                "required_flags": [],
                "optional_flags": {
                    "--staging-days": "keep staging files newer than N days (default 7)",
                    "--log-days": "keep log files newer than N days (default 30)",
                    "--no-backups": "skip backup cleanup",
                    "--no-temp": "skip temp file cleanup",
                    "--yes": "skip confirmation prompt",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "staging_days": {"type": "integer", "default": 7},
                        "log_days": {"type": "integer", "default": 30},
                        "no_backups": {"type": "boolean", "default": False},
                        "no_temp": {"type": "boolean", "default": False},
                        "yes": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
            {
                "command": "bbman diagnostics --output json",
                "description": "Run full diagnostics; optionally save report to file.",
                "required_flags": [],
                "optional_flags": {
                    "--report-file": "save report to this file path",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "report_file": {"type": "string"},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbman status --output json",
            "bbman cleanup --yes --output json",
            "bbman diagnostics --output json",
        ],
        "output_format": "Varies by command; all wrapped in standard JSON envelope.",
        "exit_codes": {0: "success", 1: "user error", 3: "system error"},
    },

    "updates": {
        "id": "updates",
        "summary": "Check for and apply application updates.",
        "common": False,
        "workflow": ["check-updates", "update"],
        "steps": [
            {
                "command": "bbman check-updates --output json",
                "description": "Check remote for file-level changes against local installation.",
                "required_flags": [],
                "optional_flags": {
                    "--branch": "branch to check (default: main)",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "branch": {"type": "string", "default": "main"},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
            {
                "command": "bbman update --yes --output json",
                "description": "Apply updates. Use --yes to skip confirmation.",
                "required_flags": [],
                "optional_flags": {
                    "--branch": "branch to update from (default: main)",
                    "--method": "git or download",
                    "--yes": "skip confirmation",
                    "--output": "text or json",
                },
                "valid_values": {
                    "--method": ["git", "download"],
                    "--output": ["text", "json"],
                },
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "branch": {"type": "string", "default": "main"},
                        "method": {"type": "string", "enum": ["git", "download"], "default": "git"},
                        "yes": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbman check-updates --output json",
            "bbman update --yes --output json",
        ],
        "output_format": (
            '{"has_updates": true, "changed": [...], "new": [...], "removed": [...]}'
        ),
        "exit_codes": {0: "success", 1: "error checking updates"},
    },

    "dependencies": {
        "id": "dependencies",
        "summary": "Check and optionally install missing Python and system dependencies.",
        "common": False,
        "workflow": ["check-deps"],
        "steps": [
            {
                "command": "bbman check-deps --output json",
                "description": "Check required and optional dependencies.",
                "required_flags": [],
                "optional_flags": {
                    "--install": "install missing packages",
                    "--output": "text or json",
                },
                "valid_values": {"--output": ["text", "json"]},
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "install": {"type": "boolean", "default": False},
                        "output": {"type": "string", "enum": ["text", "json"]},
                    },
                    "required": [],
                },
            },
        ],
        "examples": [
            "bbman check-deps --output json",
            "bbman check-deps --install --output json",
        ],
        "output_format": (
            '{"system": {"rsync": {"ok": true, "message": "..."}, ...}, '
            '"python_packages": {"ok": true, "installed": [...], "missing": []}, '
            '"python_all_installed": true}'
        ),
        "exit_codes": {0: "all installed", 1: "missing dependencies"},
    },
}

# ---------------------------------------------------------------------------
# Accessor
# ---------------------------------------------------------------------------


def get_skill(cli: str, skill_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Return skill descriptor(s) for the given CLI.

    Level-0 (skill_id is None):
        Returns an overview dict with agent hints and a compact skills list.
        Agents should call this first to discover what the CLI can do.

    Level-1 (skill_id provided):
        Returns the full skill dict with steps, schemas, and examples.
        Returns None for unknown skill ids; caller should exit with EXIT_USER_ERROR.

    Args:
        cli:      "bbackup" or "bbman"
        skill_id: skill id string, or None for level-0 overview

    Returns:
        Dict on success, None when skill_id is not recognized.
    """
    registry = BBACKUP_SKILLS if cli == "bbackup" else BBMAN_SKILLS

    if skill_id is None:
        from bbackup import __version__
        return {
            "cli": cli,
            "version": __version__,
            "agent_hint": (
                f"Set BBACKUP_OUTPUT=json and BBACKUP_NO_INTERACTIVE=1 for "
                f"fully non-interactive use. "
                f"Pass --input-json '{{...}}' to supply all params as one object. "
                f"Run '{cli} skills <skill_id>' for step-by-step detail and JSON schemas."
            ),
            "skills": [
                {
                    "id": s["id"],
                    "summary": s["summary"],
                    "common": s["common"],
                }
                for s in registry.values()
            ],
        }

    return registry.get(skill_id)
