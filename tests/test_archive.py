"""
Tests for bbackup.archive: solid archive create/unpack and naming helpers.
"""

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bbackup.archive import (
    create_solid_archive,
    is_solid_archive_name,
    strip_solid_archive_suffix,
    unpack_solid_archive,
)


class TestNamingHelpers:
    def test_is_solid_archive_name_tar_gz(self):
        assert is_solid_archive_name("backup_20260304_120000.tar.gz") is True
        assert is_solid_archive_name("backup_20260304_120000.tar.gz.enc") is True

    def test_is_solid_archive_name_other_formats(self):
        assert is_solid_archive_name("backup_20260304.tar.bz2") is True
        assert is_solid_archive_name("backup_20260304.tar.xz.enc") is True

    def test_is_solid_archive_name_false(self):
        assert is_solid_archive_name("backup_20260304_120000") is False
        assert is_solid_archive_name("other.tar.gz") is True  # any name with suffix

    def test_strip_solid_archive_suffix(self):
        assert strip_solid_archive_suffix("backup_20260304_120000.tar.gz") == "backup_20260304_120000"
        assert strip_solid_archive_suffix("backup_20260304_120000.tar.gz.enc") == "backup_20260304_120000"
        assert strip_solid_archive_suffix("backup_20260304_120000") == "backup_20260304_120000"


class TestCreateSolidArchive:
    def test_create_solid_archive_plain(self, tmp_path):
        backup_dir = tmp_path / "backup_20260304_120000"
        backup_dir.mkdir()
        (backup_dir / "configs").mkdir()
        (backup_dir / "configs" / "c1.json").write_text("{}")
        compression = {"enabled": True, "level": 6, "format": "gzip"}
        out = create_solid_archive(backup_dir, compression, encryption_config=None)
        assert out == backup_dir.parent / "backup_20260304_120000.tar.gz"
        assert out.exists()
        with tarfile.open(out, "r:gz") as tar:
            names = tar.getnames()
        assert any("configs" in n for n in names)

    def test_create_solid_archive_with_encryption_skipped_when_disabled(self, tmp_path):
        backup_dir = tmp_path / "backup_20260304_120000"
        backup_dir.mkdir()
        (backup_dir / "volumes").mkdir()
        compression = {"enabled": True, "level": 1, "format": "gzip"}
        enc = MagicMock()
        enc.enabled = False
        out = create_solid_archive(backup_dir, compression, encryption_config=enc)
        assert out.suffix == ".gz"
        assert not str(out).endswith(".enc")

    def test_create_solid_archive_removes_partial_on_failure(self, tmp_path):
        backup_dir = tmp_path / "backup_20260304_120000"
        backup_dir.mkdir()
        compression = {"enabled": True, "level": 6, "format": "gzip"}
        enc = MagicMock()
        enc.enabled = True
        with patch("bbackup.archive.EncryptionManager") as MockEnc:
            MockEnc.return_value.encrypt_file.return_value = False
            with pytest.raises(OSError):
                create_solid_archive(backup_dir, compression, encryption_config=enc)
            # Partial .tar.gz should be removed
            partial = backup_dir.parent / "backup_20260304_120000.tar.gz"
            assert not partial.exists()

    def test_create_solid_archive_preserves_existing_final_on_failure(self, tmp_path):
        backup_dir = tmp_path / "backup_20260304_120000"
        backup_dir.mkdir()
        final = backup_dir.parent / "backup_20260304_120000.tar.gz"
        final.write_bytes(b"existing")
        compression = {"enabled": True, "level": 6, "format": "gzip"}
        enc = MagicMock()
        enc.enabled = True

        with patch("bbackup.archive.EncryptionManager") as MockEnc:
            MockEnc.return_value.encrypt_file.return_value = False
            with pytest.raises(OSError):
                create_solid_archive(backup_dir, compression, encryption_config=enc)

        assert final.read_bytes() == b"existing"
        assert not final.with_name(f"{final.name}.partial").exists()


class TestUnpackSolidArchive:
    def test_unpack_returns_dir_unchanged(self, tmp_path):
        d = tmp_path / "backup_20260304"
        d.mkdir()
        unpacked, cleanup = unpack_solid_archive(d)
        assert unpacked == d
        assert cleanup is None

    def test_unpack_tar_gz(self, tmp_path):
        archive = tmp_path / "backup_20260304.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            add_dir = tmp_path / "content"
            add_dir.mkdir()
            (add_dir / "test.txt").write_text("hello")
            tar.add(add_dir, arcname="content")
        unpacked, cleanup = unpack_solid_archive(archive)
        assert cleanup is not None
        assert (unpacked / "test.txt").read_text() == "hello"
        if cleanup.exists():
            import shutil
            shutil.rmtree(cleanup, ignore_errors=True)

    def test_unpack_returns_tuple(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        unpacked, cleanup = unpack_solid_archive(d)
        assert isinstance(unpacked, Path)
        assert cleanup is None
