"""
Solid archive (single tarball) creation and unpacking.
Creates one compressed tarball from a backup dir; optionally encrypts the whole file.
Purpose: Support single-file upload to remotes (e.g. rclone) instead of many small files.
Created: 2026-03-04
Last Updated: 2026-03-04
"""

import gzip
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .encryption import EncryptionManager
from .logging import get_logger

logger = get_logger("archive")

# Suffixes for solid archive filenames (Gap 10: single source of truth)
SOLID_ARCHIVE_SUFFIXES = (
    ".tar.gz",
    ".tar.gz.enc",
    ".tar.bz2",
    ".tar.bz2.enc",
    ".tar.xz",
    ".tar.xz.enc",
)


def is_solid_archive_name(name: str) -> bool:
    """Return True if name looks like a solid archive (e.g. backup_*.tar.gz or .tar.gz.enc)."""
    return any(name.endswith(s) for s in SOLID_ARCHIVE_SUFFIXES)


def strip_solid_archive_suffix(name: str) -> str:
    """Return base name with solid-archive suffix removed for date parsing (e.g. backup_20260304_120000)."""
    for suffix in SOLID_ARCHIVE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _compression_ext(format: str) -> str:
    """Return file extension for compression format (e.g. gz, bz2, xz)."""
    return {"gzip": "gz", "bzip2": "bz2", "xz": "xz"}.get(format, "gz")


def _tar_mode(format: str) -> str:
    """Return tarfile mode for format."""
    return {"gzip": "w:gz", "bzip2": "w:bz2", "xz": "w:xz"}.get(format, "w:gz")


def create_solid_archive(
    backup_dir: Path,
    compression_config: Dict[str, Any],
    encryption_config: Optional[Any] = None,
) -> Path:
    """
    Create a single compressed tarball from backup_dir; optionally encrypt the whole file.

    Args:
        backup_dir: Directory tree to archive (configs/, volumes/, networks/, filesystems/).
        compression_config: Dict with enabled, level, format (from Config.get_backup_compression()).
        encryption_config: If provided and enabled, encrypt the archive to same path + .enc.

    Returns:
        Path to the final file (.tar.gz, .tar.bz2, .tar.xz, or .enc variant).

    Raises:
        OSError: On write or tar failure. Partial output is removed on failure (Gap 8).
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.is_dir():
        raise OSError(f"Not a directory: {backup_dir}")

    fmt = compression_config.get("format", "gzip")
    level = int(compression_config.get("level", 6))
    ext = _compression_ext(fmt)
    archive_path = backup_dir.parent / f"{backup_dir.name}.tar.{ext}"
    partial_archive_path = archive_path.with_name(f"{archive_path.name}.partial")
    partial_enc_path: Optional[Path] = None

    try:
        if partial_archive_path.exists():
            partial_archive_path.unlink()
        if fmt == "gzip" and level != 9:
            # Use gzip level (Gap 6)
            with open(partial_archive_path, "wb") as f:
                with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=level) as gz:
                    with tarfile.open(fileobj=gz, mode="w") as tar:
                        tar.add(backup_dir, arcname=backup_dir.name)
        else:
            # tarfile built-in compression (level not configurable for bz2/xz in same way)
            mode = _tar_mode(fmt)
            with tarfile.open(partial_archive_path, mode) as tar:
                tar.add(backup_dir, arcname=backup_dir.name)

        if encryption_config is not None and getattr(encryption_config, "enabled", False):
            enc_path = archive_path.with_suffix(archive_path.suffix + ".enc")
            partial_enc_path = enc_path.with_name(f"{enc_path.name}.partial")
            if partial_enc_path.exists():
                partial_enc_path.unlink()
            mgr = EncryptionManager(encryption_config)
            if not mgr.encrypt_file(partial_archive_path, partial_enc_path):
                raise OSError("Encryption of archive failed")
            try:
                partial_archive_path.unlink()
            except OSError as e:
                logger.warning(f"Could not remove intermediate archive after encrypt: {e}")
            os.replace(partial_enc_path, enc_path)
            archive_path = enc_path
        else:
            os.replace(partial_archive_path, archive_path)

        return archive_path
    except Exception:
        for path in (partial_archive_path, partial_enc_path):
            if path is not None and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
        raise


def unpack_solid_archive(
    archive_path: Path,
    dest_dir: Optional[Path] = None,
    encryption_config: Optional[Any] = None,
) -> tuple:
    """
    Unpack a solid archive (or return path if it is already a directory).

    Args:
        archive_path: Path to .tar.gz, .tar.gz.enc, .tar.bz2, .tar.xz, or directory.
        dest_dir: If set, extract here; else use a temp directory (caller must clean up).
        encryption_config: Required if archive_path has .enc suffix; used to decrypt.

    Returns:
        (unpacked_path, temp_root_to_remove): Path to unpacked backup root; optional temp dir
        to remove in finally (non-None only when dest_dir was None).

    Raises:
        OSError: On read or extract failure. Temp .tar.gz from decrypt is removed in finally (Gap 8).
    """
    archive_path = Path(archive_path)
    if archive_path.is_dir():
        return (archive_path, None)

    if not archive_path.is_file():
        raise OSError(f"Not a file or directory: {archive_path}")

    temp_tar: Optional[Path] = None
    use_temp_dest = dest_dir is None
    temp_root_to_remove: Optional[Path] = None
    if use_temp_dest:
        dest_dir = Path(tempfile.mkdtemp(prefix="bbackup_unpack_"))
        temp_root_to_remove = dest_dir

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        to_extract: Optional[Path] = archive_path
        if archive_path.suffix == ".enc" or archive_path.name.endswith(".tar.gz.enc") or archive_path.name.endswith(".tar.bz2.enc") or archive_path.name.endswith(".tar.xz.enc"):
            if encryption_config is None or not getattr(encryption_config, "enabled", False):
                raise OSError(
                    "Backup file is encrypted; set encryption.enabled to true and ensure keys are configured."
                )
            # Preserve inner compression format for temp file
            if archive_path.name.endswith(".tar.gz.enc"):
                temp_suffix = ".tar.gz"
            elif archive_path.name.endswith(".tar.bz2.enc"):
                temp_suffix = ".tar.bz2"
            elif archive_path.name.endswith(".tar.xz.enc"):
                temp_suffix = ".tar.xz"
            else:
                temp_suffix = ".tar.gz"
            fd, temp_tar_path = tempfile.mkstemp(suffix=temp_suffix, prefix="bbackup_decrypt_")
            temp_tar = Path(temp_tar_path)
            try:
                import os as _os
                _os.close(fd)
                mgr = EncryptionManager(encryption_config)
                if not mgr.decrypt_file(archive_path, temp_tar):
                    raise OSError("Decryption of archive failed")
                to_extract = temp_tar
            except Exception:
                if temp_tar and temp_tar.exists():
                    temp_tar.unlink(missing_ok=True)
                raise

        if to_extract is None:
            raise OSError("No archive to extract")

        # Determine mode from extension
        name = to_extract.name
        if name.endswith(".tar.gz"):
            mode = "r:gz"
        elif name.endswith(".tar.bz2"):
            mode = "r:bz2"
        elif name.endswith(".tar.xz"):
            mode = "r:xz"
        else:
            mode = "r:*"

        with tarfile.open(to_extract, mode) as tar:
            tar.extractall(dest_dir, filter="data")

        # Tar typically contains one top-level dir (backup_YYYYMMDD_HHMMSS); return that if present
        items = list(dest_dir.iterdir())
        if len(items) == 1 and items[0].is_dir():
            return (items[0], temp_root_to_remove)
        return (dest_dir, temp_root_to_remove)
    finally:
        if temp_tar is not None and temp_tar.exists():
            try:
                temp_tar.unlink()
            except OSError:
                pass
