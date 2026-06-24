import json
import textwrap
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bbackup.cli import cli
from bbackup.config import Config
from bbackup.snapshot import (
    ResticRunner,
    SnapshotError,
    check_snapshot_profile,
    discover_git_repos,
    load_state,
    purge_plan,
    reconcile_repos,
    retire_repo,
    snapshot_plan,
    state_file,
)


def write_snapshot_config(tmp_path, extra=""):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(textwrap.dedent(f"""
        snapshot_profiles:
          essentials-daily:
            engine: restic
            host_id: test-host
            repository: rclone:ALIEN001-GD:backups/SCAR01/restic/essentials-daily
            cache_dir: {tmp_path}/cache
            state_dir: {tmp_path}/state
            password_file: {tmp_path}/password
            retry_lock: 7m
            repo_homes:
              - {tmp_path}/repos
            explicit_repos:
              - {tmp_path}/myrig
            include_paths:
              - {tmp_path}/Documents
            exclude_paths:
              - {tmp_path}/repos/archives
            tags:
              - scar01
            {extra}
    """))
    (tmp_path / "password").write_text("secret\n")
    (tmp_path / "password").chmod(0o600)
    (tmp_path / "cache").mkdir()
    (tmp_path / "state").mkdir()
    return cfg_file


def init_git_repo(path):
    path.mkdir(parents=True)
    (path / "README.md").write_text("test\n")
    import subprocess

    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "init"], check=True, capture_output=True)


def test_snapshot_profile_config_parsed(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    assert profile.engine == "restic"
    assert profile.repository.startswith("rclone:")
    assert profile.repo_homes == [f"{tmp_path}/repos"]
    assert profile.explicit_repos == [f"{tmp_path}/myrig"]
    assert profile.exclude_paths == [f"{tmp_path}/repos/archives"]


def test_restic_backup_args_include_required_flags(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    args = ResticRunner(profile).backup_args("/tmp/source", ["bbackup", "profile=essentials-daily"])
    assert args[:3] == ["restic", "-r", profile.repository]
    assert "--password-file" in args
    assert "--cache-dir" in args
    assert "--json" in args
    assert "--retry-lock" in args
    assert "7m" in args
    assert "--host" in args
    assert "test-host" in args
    assert "--tag" in args
    assert "--exclude" in args


def test_discover_git_repos_uses_immediate_children_and_explicit_roots(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    (tmp_path / "repos" / "not-git").mkdir(parents=True)
    init_git_repo(tmp_path / "myrig")

    discovered = discover_git_repos(profile)
    paths = {repo.path for repo in discovered}
    assert str((tmp_path / "repos" / "repo-a").resolve()) in paths
    assert str((tmp_path / "myrig").resolve()) in paths
    assert str((tmp_path / "repos" / "not-git").resolve()) not in paths


def test_discover_git_repos_skips_excluded_repo_home_children(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    profile.exclude_paths.append(f"{tmp_path}/repos/starred-repos")
    init_git_repo(tmp_path / "repos" / "repo-a")
    init_git_repo(tmp_path / "repos" / "starred-repos")

    discovered = discover_git_repos(profile)
    paths = {repo.path for repo in discovered}
    assert str((tmp_path / "repos" / "repo-a").resolve()) in paths
    assert str((tmp_path / "repos" / "starred-repos").resolve()) not in paths


def test_reconcile_marks_deleted_repo_retired_only_after_snapshot(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    discovered = discover_git_repos(profile)
    first = reconcile_repos(profile, discovered)
    repo_id = first["active_repo_ids"][0]
    state = load_state(profile)
    state["repos"][repo_id]["successful_snapshot_ids"] = ["abc123"]
    from bbackup.snapshot import save_state

    save_state(profile, state)

    import shutil

    shutil.rmtree(tmp_path / "repos" / "repo-a")
    result = reconcile_repos(profile, [])
    assert repo_id in result["retired_repo_ids"]
    assert result["alerts"] == []


def test_reconcile_alerts_when_deleted_repo_has_no_successful_snapshot(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    discovered = discover_git_repos(profile)
    reconcile_repos(profile, discovered)

    import shutil

    shutil.rmtree(tmp_path / "repos" / "repo-a")
    result = reconcile_repos(profile, [])
    assert result["alerts"][0]["code"] == "missing_without_snapshot"


def test_path_reuse_with_different_fingerprint_alerts(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    discovered = discover_git_repos(profile)
    first = reconcile_repos(profile, discovered)
    repo_id = first["active_repo_ids"][0]
    state = load_state(profile)
    state["repos"][repo_id]["status"] = "retired"
    state["repos"][repo_id]["successful_snapshot_ids"] = ["abc123"]
    state["repos"][repo_id]["fingerprint"] = "different"
    from bbackup.snapshot import save_state

    save_state(profile, state)

    result = reconcile_repos(profile, discovered)
    assert result["alerts"][0]["code"] == "path_reuse_conflict"


def test_purge_plan_refuses_active_repo(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    result = reconcile_repos(profile, discover_git_repos(profile))
    repo_id = result["active_repo_ids"][0]
    try:
        purge_plan(profile, repo_id)
    except SnapshotError as exc:
        assert "active" in str(exc)
    else:
        raise AssertionError("purge_plan should refuse active repos")


def test_purge_plan_for_retired_repo_is_dry_run_first(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")
    result = reconcile_repos(profile, discover_git_repos(profile))
    repo_id = result["active_repo_ids"][0]
    state = load_state(profile)
    state["repos"][repo_id]["successful_snapshot_ids"] = ["abc123"]
    from bbackup.snapshot import save_state

    save_state(profile, state)
    retire_repo(profile, repo_id)
    plan = purge_plan(profile, repo_id)
    assert plan["dry_run_required"] is True
    assert "--dry-run" in plan["forget_args"]
    assert "--dry-run" not in plan["destructive_args_after_confirmation"]
    assert f"repo_id={repo_id}" in plan["forget_args"]


def test_snapshot_plan_cli_json(tmp_path):
    cfg_file = write_snapshot_config(tmp_path)
    init_git_repo(tmp_path / "repos" / "repo-a")
    result = CliRunner().invoke(
        cli,
        ["--config", str(cfg_file), "snapshot", "plan", "--profile", "essentials-daily", "--output", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["repos"][0]["repo_id"]


def test_snapshot_plan_does_not_persist_state(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    init_git_repo(tmp_path / "repos" / "repo-a")

    plan = snapshot_plan(profile)

    assert plan["repos"]
    assert not state_file(profile).exists()


def test_snapshot_init_dry_run_cli_json(tmp_path):
    cfg_file = write_snapshot_config(tmp_path)
    result = CliRunner().invoke(
        cli,
        [
            "--config", str(cfg_file),
            "snapshot", "init",
            "--profile", "essentials-daily",
            "--dry-run",
            "--output", "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["dry_run"] is True
    assert data["data"]["args"][-1] == "init"


def test_snapshot_health_reports_profile_dependencies(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")
        result = check_snapshot_profile(profile)
    assert result["ok"] is True
    assert result["checks"]["restic"]["ok"] is True
    assert result["checks"]["rclone"]["ok"] is True


def test_snapshot_health_rejects_google_drive_remote_without_client_id(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(returncode=0, stdout="[ALIEN001-GD]\ntype = drive\nscope = drive\n", stderr="")
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        result = check_snapshot_profile(profile)

    assert result["ok"] is False
    assert result["checks"]["rclone_drive_client_id"]["ok"] is False
    assert "no client_id" in result["checks"]["rclone_drive_client_id"]["message"]


def test_snapshot_health_accepts_google_drive_remote_with_client_id(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(
                returncode=0,
                stdout="[ALIEN001-GD]\ntype = drive\nclient_id = example.apps.googleusercontent.com\n",
                stderr="",
            )
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        result = check_snapshot_profile(profile)

    assert result["ok"] is True
    assert result["checks"]["rclone_drive_client_id"]["ok"] is True
