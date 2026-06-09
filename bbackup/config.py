"""
Configuration management for bbackup.
Handles loading and merging of YAML config files with CLI overrides.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class BackupScope:
    """Backup scope configuration."""
    containers: bool = True
    volumes: bool = True
    networks: bool = True
    configs: bool = True
    filesystems: bool = True


@dataclass
class BackupSet:
    """Backup set definition."""
    name: str
    description: str = ""
    containers: List[str] = field(default_factory=list)
    scope: BackupScope = field(default_factory=BackupScope)


@dataclass
class FilesystemTarget:
    """A single filesystem path to back up."""
    name: str
    path: str
    excludes: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class FilesystemBackupSet:
    """Named set of filesystem targets."""
    name: str
    description: str = ""
    targets: List[FilesystemTarget] = field(default_factory=list)


RCLONE_OPTIONS_CAP = 32
RCLONE_DEFAULT_TRANSFERS = 8
RCLONE_DEFAULT_CHECKERS = 8


def _clamp_rclone_int(value: Any, name: str, default: int) -> int:
    """Clamp a config value to [1, RCLONE_OPTIONS_CAP]; use default if invalid."""
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return 1
    if n > RCLONE_OPTIONS_CAP:
        return RCLONE_OPTIONS_CAP
    return n


@dataclass
class RcloneOptions:
    """
    Rclone transfer and concurrency options.
    Recommended defaults: transfers=8, checkers=8. Values are clamped to [1, 32].
    """
    transfers: int = RCLONE_DEFAULT_TRANSFERS
    checkers: int = RCLONE_DEFAULT_CHECKERS


@dataclass
class RemoteStorage:
    """Remote storage configuration."""
    name: str
    enabled: bool = False
    type: str = "local"  # local, rclone, sftp
    path: str = ""
    compression: bool = True
    # SFTP specific
    host: Optional[str] = None
    port: int = 22
    user: Optional[str] = None
    key_file: Optional[str] = None
    # rclone specific
    remote_name: Optional[str] = None
    rclone_options: Optional[RcloneOptions] = None


@dataclass
class RetentionPolicy:
    """Backup retention policy."""
    daily: int = 7
    weekly: int = 4
    monthly: int = 12
    max_storage_gb: int = 0
    warning_threshold_percent: int = 80
    cleanup_threshold_percent: int = 90
    cleanup_strategy: str = "oldest_first"


@dataclass
class IncrementalSettings:
    """Incremental backup settings."""
    enabled: bool = True
    use_link_dest: bool = True
    min_file_size: int = 1048576  # 1MB


@dataclass
class EncryptionSettings:
    """Encryption settings."""
    enabled: bool = False
    method: str = "symmetric"  # symmetric, asymmetric, both
    symmetric: Dict[str, Any] = field(default_factory=dict)
    asymmetric: Dict[str, Any] = field(default_factory=dict)
    encrypt_volumes: bool = True
    encrypt_configs: bool = True
    encrypt_networks: bool = True


class Config:
    """Main configuration class."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config()
        self.data: Dict[str, Any] = {}
        self.backup_sets: Dict[str, BackupSet] = {}
        self.filesystem_sets: Dict[str, FilesystemBackupSet] = {}
        self.remotes: Dict[str, RemoteStorage] = {}
        self.retention = RetentionPolicy()
        self.incremental = IncrementalSettings()
        self.encryption = EncryptionSettings()
        self.scope = BackupScope()
        self.rclone_default_options: Optional[RcloneOptions] = None
        self.solid_archive: bool = False
        
        if self.config_path and os.path.exists(self.config_path):
            self.load()
        else:
            self._load_defaults()
    
    def _find_config(self) -> Optional[str]:
        """Find configuration file in standard locations."""
        config_locations = [
            os.path.expanduser("~/.config/bbackup/config.yaml"),
            os.path.expanduser("~/.bbackup/config.yaml"),
            "/etc/bbackup/config.yaml",
            os.path.join(os.getcwd(), "config.yaml"),
        ]
        
        for path in config_locations:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_defaults(self):
        """Load default configuration."""
        self.data = {
            "backup": {
                "local_staging": "/tmp/bbackup_staging",
                "solid_archive": False,
                "compression": {"enabled": True, "level": 6, "format": "gzip"},
                "default_scope": {
                    "containers": True,
                    "volumes": True,
                    "networks": True,
                    "configs": True,
                },
            },
            "retention": {
                "daily": 7,
                "weekly": 4,
                "monthly": 12,
                "max_storage_gb": 0,
            },
            "incremental": {
                "enabled": True,
                "use_link_dest": True,
            },
        }
        self._parse_config()
    
    def load(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.data = yaml.safe_load(f) or {}
            self._parse_config()
        except Exception as e:
            raise ValueError(f"Failed to load config from {self.config_path}: {e}")
    
    def _parse_config(self):
        """Parse loaded configuration into dataclasses."""
        # Parse backup scope and solid_archive
        if "backup" in self.data:
            backup = self.data["backup"]
            self.solid_archive = backup.get("solid_archive", False)
            if "default_scope" in backup:
                scope = backup["default_scope"]
                self.scope = BackupScope(
                    containers=scope.get("containers", True),
                    volumes=scope.get("volumes", True),
                    networks=scope.get("networks", True),
                    configs=scope.get("configs", True),
                    filesystems=scope.get("filesystems", True),
                )
        
        # Parse backup sets
        if "backup" in self.data and "backup_sets" in self.data["backup"]:
            for name, set_data in self.data["backup"]["backup_sets"].items():
                scope_data = set_data.get("scope", {})
                scope = BackupScope(
                    containers=scope_data.get("containers", True),
                    volumes=scope_data.get("volumes", True),
                    networks=scope_data.get("networks", True),
                    configs=scope_data.get("configs", True),
                    filesystems=scope_data.get("filesystems", True),
                )
                self.backup_sets[name] = BackupSet(
                    name=name,
                    description=set_data.get("description", ""),
                    containers=set_data.get("containers", []),
                    scope=scope,
                )

        # Parse filesystem backup sets
        for set_name, set_data in self.data.get("filesystem", {}).items():
            targets = [
                FilesystemTarget(
                    name=t["name"],
                    path=t["path"],
                    excludes=t.get("excludes", []),
                    enabled=t.get("enabled", True),
                )
                for t in set_data.get("targets", [])
            ]
            self._validate_unique_filesystem_target_names(targets)
            self.filesystem_sets[set_name] = FilesystemBackupSet(
                name=set_name,
                description=set_data.get("description", ""),
                targets=targets,
            )

        # Parse top-level rclone default options
        if "rclone" in self.data:
            rclone_data = self.data["rclone"]
            if isinstance(rclone_data, dict) and "default_options" in rclone_data:
                do = rclone_data["default_options"]
                if isinstance(do, dict):
                    self.rclone_default_options = RcloneOptions(
                        transfers=_clamp_rclone_int(
                            do.get("transfers"), "transfers", RCLONE_DEFAULT_TRANSFERS
                        ),
                        checkers=_clamp_rclone_int(
                            do.get("checkers"), "checkers", RCLONE_DEFAULT_CHECKERS
                        ),
                    )

        # Parse remote storage
        if "remotes" in self.data:
            for name, remote_data in self.data["remotes"].items():
                rclone_opts: Optional[RcloneOptions] = None
                if remote_data.get("type") == "rclone" and "rclone_options" in remote_data:
                    ro = remote_data["rclone_options"]
                    if isinstance(ro, dict):
                        rclone_opts = RcloneOptions(
                            transfers=_clamp_rclone_int(
                                ro.get("transfers"), "transfers", RCLONE_DEFAULT_TRANSFERS
                            ),
                            checkers=_clamp_rclone_int(
                                ro.get("checkers"), "checkers", RCLONE_DEFAULT_CHECKERS
                            ),
                        )
                self.remotes[name] = RemoteStorage(
                    name=name,
                    enabled=remote_data.get("enabled", False),
                    type=remote_data.get("type", "local"),
                    path=remote_data.get("path", ""),
                    compression=remote_data.get("compression", True),
                    host=remote_data.get("host"),
                    port=remote_data.get("port", 22),
                    user=remote_data.get("user"),
                    key_file=remote_data.get("key_file"),
                    remote_name=remote_data.get("remote_name"),
                    rclone_options=rclone_opts,
                )
        
        # Parse retention policy
        if "retention" in self.data:
            ret = self.data["retention"]
            self.retention = RetentionPolicy(
                daily=ret.get("daily", 7),
                weekly=ret.get("weekly", 4),
                monthly=ret.get("monthly", 12),
                max_storage_gb=ret.get("max_storage_gb", 0),
                warning_threshold_percent=ret.get("warning_threshold_percent", 80),
                cleanup_threshold_percent=ret.get("cleanup_threshold_percent", 90),
                cleanup_strategy=ret.get("cleanup_strategy", "oldest_first"),
            )
        
        # Parse incremental settings
        if "incremental" in self.data:
            inc = self.data["incremental"]
            self.incremental = IncrementalSettings(
                enabled=inc.get("enabled", True),
                use_link_dest=inc.get("use_link_dest", True),
                min_file_size=inc.get("min_file_size", 1048576),
            )

        # Parse encryption settings
        if "encryption" in self.data:
            enc = self.data["encryption"]
            self.encryption = EncryptionSettings(
                enabled=enc.get("enabled", False),
                method=enc.get("method", "symmetric"),
                symmetric=enc.get("symmetric", {}),
                asymmetric=enc.get("asymmetric", {}),
                encrypt_volumes=enc.get("encrypt_volumes", True),
                encrypt_configs=enc.get("encrypt_configs", True),
                encrypt_networks=enc.get("encrypt_networks", True),
            )

    def _validate_unique_filesystem_target_names(self, targets: List[FilesystemTarget]) -> None:
        """Reject duplicate filesystem target names that would overwrite each other."""
        seen = set()
        for target in targets:
            if target.name in seen:
                raise ValueError(f"Duplicate filesystem target name: {target.name}")
            seen.add(target.name)
    
    def get_staging_dir(self) -> str:
        """Get local staging directory."""
        return self.data.get("backup", {}).get("local_staging", "/tmp/bbackup_staging")

    def get_backup_compression(self) -> Dict[str, Any]:
        """
        Return backup compression config with defaults for solid archive and metadata.
        Keys: enabled (bool), level (int), format (str: gzip, bzip2, xz).
        """
        raw = self.data.get("backup", {}).get("compression", {})
        return {
            "enabled": raw.get("enabled", True),
            "level": int(raw.get("level", 6)),
            "format": raw.get("format", "gzip"),
        }
    
    def get_backup_set(self, name: str) -> Optional[BackupSet]:
        """Get backup set by name."""
        return self.backup_sets.get(name)
    
    def get_enabled_remotes(self) -> List[RemoteStorage]:
        """Get list of enabled remote storage destinations."""
        return [r for r in self.remotes.values() if r.enabled]


def get_effective_rclone_options(config: "Config", remote: RemoteStorage) -> RcloneOptions:
    """
    Return effective rclone options for a remote: per-remote overrides global
    default, which overrides built-in defaults (transfers=8, checkers=8).
    """
    if remote.rclone_options is not None:
        return remote.rclone_options
    if config.rclone_default_options is not None:
        return config.rclone_default_options
    return RcloneOptions()
