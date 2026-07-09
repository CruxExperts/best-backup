import json
import hashlib
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
    save_state,
    snapshot_check,
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
            repository: rclone:example-drive:backups/WORKSTATION01/restic/essentials-daily
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
              - workstation01
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


def test_snapshot_profile_default_drive_client_opt_in_requires_boolean_true(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path, 'allow_default_rclone_drive_client: "false"')))
    profile = cfg.snapshot_profiles["essentials-daily"]
    assert profile.allow_default_rclone_drive_client is False


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


def test_reconcile_updates_active_repo_after_new_commit(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    repo_path = tmp_path / "repos" / "repo-a"
    init_git_repo(repo_path)
    first = reconcile_repos(profile, discover_git_repos(profile))
    repo_id = first["active_repo_ids"][0]

    (repo_path / "README.md").write_text("changed\n")
    import subprocess

    subprocess.run(["git", "-C", str(repo_path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo_path), "commit", "-m", "change"], check=True, capture_output=True)
    second = reconcile_repos(profile, discover_git_repos(profile))

    assert second["alerts"] == []
    assert second["active_repo_ids"] == [repo_id]
    state = load_state(profile)
    assert state["repos"][repo_id]["head"]


def test_reconcile_migrates_legacy_head_derived_repo_id(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    repo_path = tmp_path / "repos" / "repo-a"
    init_git_repo(repo_path)
    discovered = discover_git_repos(profile)
    repo = discovered[0]
    legacy_fingerprint = repo.legacy_fingerprint
    legacy_repo_id = repo.legacy_repo_id
    assert legacy_repo_id != repo.repo_id

    save_state(profile, {
        "repos": {
            legacy_repo_id: {
                "repo_id": legacy_repo_id,
                "path": repo.path,
                "fingerprint": legacy_fingerprint,
                "origin": repo.origin,
                "head": repo.head,
                "status": "active",
                "successful_snapshot_ids": ["old-snapshot"],
            }
        }
    })

    plan = snapshot_plan(profile)
    assert plan["repos"][0]["repo_id"] == repo.repo_id
    assert f"repo_id={repo.repo_id}" in plan["repos"][0]["args"]

    result = reconcile_repos(profile, discovered)
    state = load_state(profile)
    assert result["active_repo_ids"] == [repo.repo_id]
    assert legacy_repo_id not in state["repos"]
    assert state["repos"][repo.repo_id]["successful_snapshot_ids"] == ["old-snapshot"]


def test_reconcile_blocks_unknown_active_same_path_identity_change(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    repo_path = tmp_path / "repos" / "repo-a"
    init_git_repo(repo_path)
    repo = discover_git_repos(profile)[0]
    conflicting_fingerprint = hashlib.sha256(b"not-this-repo").hexdigest()
    conflicting_repo_id = hashlib.sha256(f"{repo.origin or repo.path}:{conflicting_fingerprint}".encode("utf-8")).hexdigest()[:16]

    save_state(profile, {
        "repos": {
            conflicting_repo_id: {
                "repo_id": conflicting_repo_id,
                "path": repo.path,
                "fingerprint": conflicting_fingerprint,
                "origin": repo.origin,
                "head": repo.head,
                "status": "active",
                "successful_snapshot_ids": ["old-snapshot"],
            }
        }
    })

    plan = snapshot_plan(profile)

    assert plan["repos"] == []
    assert plan["alerts"][0]["code"] == "active_path_identity_conflict"


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


def test_snapshot_commands_accept_required_options_from_input_json(tmp_path):
    cfg_file = write_snapshot_config(tmp_path)
    init_git_repo(tmp_path / "repos" / "repo-a")
    cfg = Config(config_path=str(cfg_file))
    profile = cfg.snapshot_profiles["essentials-daily"]
    repo_id = reconcile_repos(profile, discover_git_repos(profile))["active_repo_ids"][0]
    state = load_state(profile)
    state["repos"][repo_id]["successful_snapshot_ids"] = ["abc123"]
    save_state(profile, state)

    runner = CliRunner()
    commands = [
        ("plan", {"profile": "essentials-daily", "output": "json"}),
        ("init", {"profile": "essentials-daily", "dry_run": True, "output": "json"}),
        ("run", {"profile": "essentials-daily", "dry_run": True, "output": "json"}),
        (
            "check",
            {
                "profile": "essentials-daily",
                "read_data_subset": "5%",
                "dry_run": True,
                "output": "json",
            },
        ),
        (
            "restore",
            {
                "profile": "essentials-daily",
                "snapshot_id": "latest",
                "target": str(tmp_path / "restore-target"),
                "dry_run": True,
                "output": "json",
            },
        ),
        ("retire", {"profile": "essentials-daily", "repo_id": repo_id, "output": "json"}),
        ("purge-plan", {"profile": "essentials-daily", "repo_id": repo_id, "output": "json"}),
        ("schedule", {"profile": "essentials-daily", "output": "json"}),
    ]

    for command, payload in commands:
        result = runner.invoke(
            cli,
            [
                "--config", str(cfg_file),
                "snapshot", command,
                "--input-json", json.dumps(payload),
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True


def test_snapshot_command_missing_json_required_param_returns_json_error(tmp_path):
    cfg_file = write_snapshot_config(tmp_path)
    result = CliRunner().invoke(
        cli,
        [
            "--config", str(cfg_file),
            "snapshot", "restore",
            "--input-json", json.dumps({"profile": "essentials-daily", "output": "json"}),
        ],
    )

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert "Missing required option: --snapshot-id" in data["errors"][0]


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
            return MagicMock(returncode=0, stdout="[example-drive]\ntype = drive\nscope = drive\n", stderr="")
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
                stdout="[example-drive]\ntype = drive\nclient_id = example.apps.googleusercontent.com\n",
                stderr="",
            )
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        result = check_snapshot_profile(profile)

    assert result["ok"] is True
    assert result["checks"]["rclone_drive_client_id"]["ok"] is True


def test_snapshot_health_accepts_default_drive_client_when_profile_allows_it(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path, "allow_default_rclone_drive_client: true")))
    profile = cfg.snapshot_profiles["essentials-daily"]

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(returncode=0, stdout="[example-drive]\ntype = drive\nscope = drive\n", stderr="")
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        result = check_snapshot_profile(profile)

    assert result["ok"] is True
    assert result["checks"]["rclone_drive_client_id"]["ok"] is True
    assert "explicit profile configuration" in result["checks"]["rclone_drive_client_id"]["message"]


def test_snapshot_check_enforces_google_drive_client_id_or_opt_in(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(returncode=0, stdout="[example-drive]\ntype = drive\nscope = drive\n", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        try:
            snapshot_check(profile)
        except SnapshotError as exc:
            assert "no client_id" in str(exc)
        else:
            raise AssertionError("snapshot_check should enforce Google Drive client_id")


def test_snapshot_check_preflight_rejects_wrong_hostname(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(
                returncode=0,
                stdout="[example-drive]\ntype = drive\nclient_id = example.apps.googleusercontent.com\n",
                stderr="",
            )
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="other-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        try:
            snapshot_check(profile)
        except SnapshotError as exc:
            assert "hostname" in str(exc)
        else:
            raise AssertionError("snapshot_check should reject profiles for a different host")


def test_snapshot_check_preflight_rejects_permissive_password_file(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    (tmp_path / "password").chmod(0o644)

    def run_side_effect(args, **kwargs):
        if args[:3] == ["rclone", "config", "show"]:
            return MagicMock(
                returncode=0,
                stdout="[example-drive]\ntype = drive\nclient_id = example.apps.googleusercontent.com\n",
                stderr="",
            )
        return MagicMock(returncode=0, stdout="restic 0.19.0\n", stderr="")

    with patch("bbackup.snapshot.shutil.which", return_value="/usr/bin/tool"), \
         patch("bbackup.snapshot.socket.gethostname", return_value="test-host"), \
         patch("bbackup.snapshot.subprocess.run", side_effect=run_side_effect):
        try:
            snapshot_check(profile)
        except SnapshotError as exc:
            assert "password file must not be group/world accessible" in str(exc)
        else:
            raise AssertionError("snapshot_check should reject permissive password files")


def test_schedule_units_include_matching_services_for_all_timers(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(
        tmp_path,
        (
            'schedule:\n'
            '              daily_time: "02:15"\n'
            '              maintenance_time: "Sun 04:30"\n'
            '              verification_time: "monthly"\n'
            '              verification_read_data_subset: "10%"'
        ),
    )))
    profile = cfg.snapshot_profiles["essentials-daily"]
    from bbackup.snapshot import schedule_units

    units = schedule_units(profile)

    assert "bbackup-test-host-essentials-daily.service" in units
    assert "bbackup-test-host-essentials-daily.timer" in units
    assert "bbackup-test-host-essentials-daily-maintenance.service" in units
    assert "bbackup-test-host-essentials-daily-maintenance.timer" in units
    assert "bbackup-test-host-essentials-daily-verification.service" in units
    assert "bbackup-test-host-essentials-daily-verification.timer" in units
    assert "snapshot run --profile essentials-daily" in units["bbackup-test-host-essentials-daily.service"]
    assert "snapshot check --profile essentials-daily\n" in units[
        "bbackup-test-host-essentials-daily-maintenance.service"
    ]
    assert "--read-data-subset 10%%" in units["bbackup-test-host-essentials-daily-verification.service"]


def test_schedule_units_escape_default_percent_in_verification_subset(tmp_path):
    cfg = Config(config_path=str(write_snapshot_config(tmp_path)))
    profile = cfg.snapshot_profiles["essentials-daily"]
    from bbackup.snapshot import schedule_units

    units = schedule_units(profile)

    assert "--read-data-subset 5%%" in units["bbackup-test-host-essentials-daily-verification.service"]
