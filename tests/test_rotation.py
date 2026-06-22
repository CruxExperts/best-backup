"""
Tests for bbackup.rotation - BackupRotation age categorization, retention
filtering, storage quota, rclone storage calc, and delete paths.
Created: 2026-02-26
Last Updated: 2026-02-26
"""

import json
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from bbackup.config import Config, RemoteStorage, RetentionPolicy
from bbackup.rotation import BackupRotation


def make_rotation(daily=7, weekly=4, monthly=12, max_gb=0):
    ret = RetentionPolicy(daily=daily, weekly=weekly, monthly=monthly, max_storage_gb=max_gb)
    return BackupRotation(retention=ret)


def make_remote(type_="local", remote_name=None, path=""):
    return RemoteStorage(
        name="test",
        enabled=True,
        type=type_,
        path=path,
        remote_name=remote_name,
    )


# ---------------------------------------------------------------------------
# TestAgeCategorization
# ---------------------------------------------------------------------------


class TestAgeCategorization:
    def test_today_is_daily(self):
        r = make_rotation()
        assert r.get_backup_age_category(datetime.now()) == "daily"

    def test_yesterday_is_daily(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=1)
        assert r.get_backup_age_category(d) == "daily"

    def test_6_days_ago_is_daily(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=6)
        assert r.get_backup_age_category(d) == "daily"

    def test_7_days_ago_is_weekly(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=7)
        assert r.get_backup_age_category(d) == "weekly"

    def test_29_days_ago_is_weekly(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=29)
        assert r.get_backup_age_category(d) == "weekly"

    def test_30_days_ago_is_monthly(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=30)
        assert r.get_backup_age_category(d) == "monthly"

    def test_365_days_ago_is_monthly(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=365)
        assert r.get_backup_age_category(d) == "monthly"


# ---------------------------------------------------------------------------
# TestShouldKeepBackup
# ---------------------------------------------------------------------------


class TestShouldKeepBackup:
    def test_keeps_daily_backup(self):
        r = make_rotation()
        assert r.should_keep_backup(datetime.now()) is True

    def test_weekly_kept_if_sunday(self):
        r = make_rotation()
        # Find a Sunday (weekday==6) that is 7-29 days ago
        d = datetime.now() - timedelta(days=14)
        # Adjust to Sunday
        offset = (6 - d.weekday()) % 7
        sunday = d + timedelta(days=offset)
        assert r.should_keep_backup(sunday) is True

    def test_weekly_not_kept_if_not_sunday(self):
        r = make_rotation()
        # Find a Monday (weekday==0) that is 7-29 days ago
        d = datetime.now() - timedelta(days=14)
        offset = (0 - d.weekday()) % 7
        monday = d + timedelta(days=offset)
        # Make sure it's still in weekly range
        age = (datetime.now() - monday).days
        if 7 <= age < 30:
            assert r.should_keep_backup(monday) is False

    def test_monthly_kept_if_first_of_month(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=31)
        first = d.replace(day=1)
        assert r.should_keep_backup(first) is True

    def test_monthly_not_kept_if_not_first(self):
        r = make_rotation()
        d = datetime.now() - timedelta(days=31)
        first = d.replace(day=1)
        # Pick a non-first day in the same month and make sure it is not Sunday
        # so it will not be selected by the weekly Sunday rule either.
        not_first = first + timedelta(days=1)
        if not_first.weekday() == 6:  # Sunday
            not_first = not_first + timedelta(days=1)
        assert r.should_keep_backup(not_first) is False


# ---------------------------------------------------------------------------
# TestParseBackupDate
# ---------------------------------------------------------------------------


class TestParseBackupDate:
    def test_valid_format(self):
        r = make_rotation()
        result = r._parse_backup_date("backup_20240115_120000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_invalid_string_returns_none(self):
        r = make_rotation()
        result = r._parse_backup_date("no_date_here")
        assert result is None

    def test_empty_string_returns_none(self):
        r = make_rotation()
        result = r._parse_backup_date("")
        assert result is None

    def test_partial_match_extracts_date(self):
        r = make_rotation()
        result = r._parse_backup_date("bkp_20231201_extra")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12


# ---------------------------------------------------------------------------
# TestFilterBackupsByRetention
# ---------------------------------------------------------------------------


class TestFilterBackupsByRetention:
    def test_daily_cap_enforced(self, tmp_path):
        r = make_rotation(daily=2)
        # Use dates from the last 6 days so they fall into "daily" category
        now = datetime.now()
        names = [
            (now - timedelta(days=i)).strftime("backup_%Y%m%d_000000")
            for i in range(5)
        ]
        keep, delete = r.filter_backups_by_retention(names, tmp_path)
        assert len(keep) <= 2

    def test_empty_list(self, tmp_path):
        r = make_rotation()
        keep, delete = r.filter_backups_by_retention([], tmp_path)
        assert keep == []
        assert delete == []

    def test_unparseable_names_excluded_from_keep(self, tmp_path):
        r = make_rotation()
        names = ["no_date_1", "no_date_2"]
        keep, delete = r.filter_backups_by_retention(names, tmp_path)
        # Unparseable names can't be categorized, so not kept
        assert len(keep) == 0

    def test_keep_plus_delete_equals_parseable_total(self, tmp_path):
        r = make_rotation(daily=2)
        now = datetime.now()
        names = [
            (now - timedelta(days=i)).strftime("backup_%Y%m%d_000000")
            for i in range(4)
        ]
        keep, delete = r.filter_backups_by_retention(names, tmp_path)
        assert len(keep) + len(delete) == len(names)


# ---------------------------------------------------------------------------
# TestCheckStorageQuota
# ---------------------------------------------------------------------------


class TestCheckStorageQuota:
    def test_quota_disabled(self, tmp_path):
        r = make_rotation(max_gb=0)
        remote = make_remote()
        result = r.check_storage_quota(remote, tmp_path)
        assert result["enabled"] is False

    def test_quota_under_warning(self, tmp_path):
        r = make_rotation(max_gb=100)
        # Create small files that are under threshold
        (tmp_path / "file.txt").write_bytes(b"x" * 100)
        remote = make_remote(path=str(tmp_path))
        result = r.check_storage_quota(remote, tmp_path)
        assert result["enabled"] is True
        assert result["warning"] is False

    def test_quota_over_warning_threshold(self, tmp_path):
        ret = RetentionPolicy(max_storage_gb=1, warning_threshold_percent=0)
        rotation = BackupRotation(retention=ret)
        (tmp_path / "bigfile.txt").write_bytes(b"x" * 1024)
        remote = make_remote(path=str(tmp_path))
        result = rotation.check_storage_quota(remote, tmp_path)
        assert result["warning"] is True


# ---------------------------------------------------------------------------
# TestCalculateLocalStorage
# ---------------------------------------------------------------------------


class TestCalculateLocalStorage:
    def test_empty_dir(self, tmp_path):
        r = make_rotation()
        assert r._calculate_local_storage(tmp_path) == 0

    def test_files_only(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"hello")
        (tmp_path / "b.txt").write_bytes(b"world!")
        r = make_rotation()
        total = r._calculate_local_storage(tmp_path)
        assert total == 11  # 5 + 6

    def test_nested_subdirs(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "file.dat").write_bytes(b"x" * 100)
        r = make_rotation()
        assert r._calculate_local_storage(tmp_path) == 100

    def test_nonexistent_path_returns_zero(self, tmp_path):
        r = make_rotation()
        assert r._calculate_local_storage(tmp_path / "nonexistent") == 0


# ---------------------------------------------------------------------------
# TestCalculateRcloneStorage
# ---------------------------------------------------------------------------


class TestCalculateRcloneStorage:
    def test_success_returns_bytes(self):
        r = make_rotation()
        remote = make_remote(type_="rclone", remote_name="myremote")
        payload = json.dumps({"bytes": 1073741824, "count": 5})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            result = r._calculate_rclone_storage(remote)
        assert result == 1073741824

    def test_returncode_nonzero_returns_zero(self):
        r = make_rotation()
        remote = make_remote(type_="rclone", remote_name="myremote")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = r._calculate_rclone_storage(remote)
        assert result == 0

    def test_no_remote_name_returns_zero(self):
        r = make_rotation()
        remote = make_remote(type_="rclone", remote_name=None)
        result = r._calculate_rclone_storage(remote)
        assert result == 0

    def test_rclone_storage_uses_config_options_when_config_present(self, tmp_path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(textwrap.dedent("""
            rclone:
              default_options:
                transfers: 10
                checkers: 5
            remotes:
              r1:
                enabled: true
                type: rclone
                remote_name: myremote
                path: backups
        """))
        cfg = Config(config_path=str(cfg_file))
        ret = RetentionPolicy()
        r = BackupRotation(retention=ret, config=cfg)
        remote = cfg.remotes["r1"]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({"bytes": 0}), stderr="")
            r._calculate_rclone_storage(remote)
        call_cmd = mock_run.call_args[0][0]
        assert "--transfers" in call_cmd
        assert "10" in call_cmd
        assert "--checkers" in call_cmd
        assert "5" in call_cmd


# ---------------------------------------------------------------------------
# TestDeleteBackup
# ---------------------------------------------------------------------------


class TestDeleteBackup:
    def test_local_exists_returns_true(self, tmp_path):
        r = make_rotation()
        backup_dir = tmp_path / "backup_20240101_000000"
        backup_dir.mkdir()
        (backup_dir / "file.txt").write_text("data")
        remote = make_remote(type_="local")
        result = r._delete_backup(remote, tmp_path, "backup_20240101_000000")
        assert result is True
        assert not backup_dir.exists()

    def test_local_missing_returns_false(self, tmp_path):
        r = make_rotation()
        remote = make_remote(type_="local")
        result = r._delete_backup(remote, tmp_path, "backup_nonexistent")
        assert result is False

    def test_rclone_success_returns_true(self):
        r = make_rotation()
        remote = make_remote(type_="rclone", remote_name="myremote")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = r._delete_backup(remote, Path("/remote"), "backup_old")
        assert result is True

    def test_rclone_failure_returns_false(self):
        r = make_rotation()
        remote = make_remote(type_="rclone", remote_name="myremote")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = r._delete_backup(remote, Path("/remote"), "backup_old")
        assert result is False

    def test_unknown_type_returns_false(self, tmp_path):
        r = make_rotation()
        remote = make_remote(type_="unknown")
        result = r._delete_backup(remote, tmp_path, "backup_whatever")
        assert result is False

    def test_local_file_backup_unlink(self, tmp_path):
        r = make_rotation()
        archive = tmp_path / "backup_20240101_120000.tar.gz"
        archive.write_bytes(b"x")
        remote = make_remote(type_="local")
        result = r._delete_backup(remote, tmp_path, "backup_20240101_120000.tar.gz")
        assert result is True
        assert not archive.exists()


# ---------------------------------------------------------------------------
# TestParseSolidArchiveDate
# ---------------------------------------------------------------------------


class TestParseSolidArchiveDate:
    def test_parse_strips_solid_archive_suffix(self):
        r = make_rotation()
        dt = r._parse_backup_date("backup_20240304_120000.tar.gz")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 3
        assert dt.day == 4

    def test_parse_strips_tar_gz_enc(self):
        r = make_rotation()
        dt = r._parse_backup_date("backup_20240304_120000.tar.gz.enc")
        assert dt is not None
        assert dt.day == 4


# ---------------------------------------------------------------------------
# TestCleanupOldBackups
# ---------------------------------------------------------------------------


class TestCleanupOldBackups:
    def test_deleted_count_matches(self, tmp_path):
        r = make_rotation()
        remote = make_remote(type_="local")
        # Create 3 backup dirs, delete 2
        for name in ["backup_A", "backup_B", "backup_C"]:
            (tmp_path / name).mkdir()
        count = r.cleanup_old_backups(remote, tmp_path, ["backup_A", "backup_B"])
        assert count == 2
        assert not (tmp_path / "backup_A").exists()
        assert not (tmp_path / "backup_B").exists()
        assert (tmp_path / "backup_C").exists()

    def test_returns_zero_for_empty_list(self, tmp_path):
        r = make_rotation()
        remote = make_remote(type_="local")
        assert r.cleanup_old_backups(remote, tmp_path, []) == 0
