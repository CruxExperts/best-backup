from dataclasses import replace
import json
import shutil
import socket
import subprocess
import textwrap

import pytest

from bbackup.config import Config
from bbackup.snapshot import (
    ResticRunner,
    common_tags,
    load_state,
    purge_plan,
    retire_repo,
    snapshot_check,
    snapshot_init,
    snapshot_restore,
    snapshot_run,
)


pytestmark = pytest.mark.integration


def _init_git_repo(path):
    path.mkdir(parents=True)
    (path / "README.md").write_text("restic integration\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "init"], check=True, capture_output=True)


def _write_local_restic_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    password_file = tmp_path / "password"
    password_file.write_text("secret\n", encoding="utf-8")
    password_file.chmod(0o600)
    cfg_file.write_text(textwrap.dedent(f"""
        snapshot_profiles:
          local-test:
            engine: restic
            host_id: {socket.gethostname()}
            repository: {tmp_path / "restic-repo"}
            cache_dir: {tmp_path / "cache"}
            state_dir: {tmp_path / "state"}
            password_file: {password_file}
            retry_lock: 1m
            repo_homes:
              - {tmp_path / "repos"}
            retention:
              active_repo_daily: 1
    """), encoding="utf-8")
    return cfg_file


def test_local_restic_snapshot_check_restore_records_state(tmp_path):
    if not shutil.which("restic"):
        pytest.skip("restic executable is unavailable")
    if subprocess.run(["restic", "version"], capture_output=True, text=True, check=False).returncode != 0:
        pytest.skip("restic executable is unavailable")

    repo_path = tmp_path / "repos" / "repo-a"
    _init_git_repo(repo_path)
    cfg = Config(config_path=str(_write_local_restic_config(tmp_path)))
    profile = cfg.snapshot_profiles["local-test"]

    init_result = snapshot_init(profile)
    assert init_result["ok"] is True

    run_result = snapshot_run(profile)
    assert run_result["success"] is True
    assert run_result["retention_results"][0]["ok"] is True
    snapshot_id = ""
    for line in run_result["results"][0]["stdout"].splitlines():
        payload = json.loads(line)
        if payload.get("message_type") == "summary":
            snapshot_id = payload["snapshot_id"]
            break
    assert snapshot_id

    check_result = snapshot_check(profile)
    assert check_result["ok"] is True

    restore_target = tmp_path / "restore"
    restore_target.mkdir()
    restore_result = snapshot_restore(profile, snapshot_id=f"{snapshot_id}:{repo_path}", target=str(restore_target))
    assert restore_result["ok"] is True, restore_result
    restored_readmes = list(restore_target.rglob("README.md"))
    assert restored_readmes
    assert any(path.read_text(encoding="utf-8") == "restic integration\n" for path in restored_readmes)

    state = load_state(profile)
    repo_id = run_result["results"][0]["repo_id"]
    assert snapshot_id in state["repos"][repo_id]["successful_snapshot_ids"]
    assert state["repos"][repo_id]["last_successful_snapshot_id"] == snapshot_id


def test_local_restic_retention_reconciles_purge_ledger(tmp_path):
    if not shutil.which("restic"):
        pytest.skip("restic executable is unavailable")
    repo_path = tmp_path / "repos" / "repo-a"
    _init_git_repo(repo_path)
    cfg = Config(config_path=str(_write_local_restic_config(tmp_path)))
    profile = cfg.snapshot_profiles["local-test"]

    assert snapshot_init(profile)["ok"] is True
    first_run = snapshot_run(profile)
    second_run = snapshot_run(profile)
    assert first_run["success"] is True
    assert second_run["success"] is True

    def snapshot_id(result):
        for line in result["results"][0]["stdout"].splitlines():
            payload = json.loads(line)
            if payload.get("message_type") == "summary":
                return payload["snapshot_id"]
        raise AssertionError("restic run did not return a snapshot ID")

    first_id = snapshot_id(first_run)
    second_id = snapshot_id(second_run)
    assert first_id != second_id
    repo_id = second_run["results"][0]["repo_id"]
    state = load_state(profile)
    assert state["repos"][repo_id]["successful_snapshot_ids"] == [second_id]

    retire_repo(profile, repo_id)
    plan = purge_plan(profile, repo_id)
    assert plan["snapshot_ids"] == [second_id]
    assert plan["forget_args"][-2:] == ["--", second_id]
    assert "--dry-run" in plan["forget_args"]



def test_local_restic_retention_cannot_remove_other_host_snapshots(tmp_path):
    if not shutil.which("restic"):
        pytest.skip("restic executable is unavailable")

    source = tmp_path / "shared-source"
    source.mkdir()
    (source / "data.txt").write_text("host isolation\n", encoding="utf-8")
    cfg = Config(config_path=str(_write_local_restic_config(tmp_path)))
    base_profile = cfg.snapshot_profiles["local-test"]
    host_a = replace(base_profile, host_id="host-a")
    host_b = replace(base_profile, host_id="host-b")

    assert snapshot_init(base_profile)["ok"] is True
    tags = common_tags(base_profile, "path", ["path_id=shared"])
    runner_b = ResticRunner(host_b)
    runner_a = ResticRunner(host_a)
    assert runner_b.run(runner_b.backup_args(str(source), tags))["ok"] is True
    assert runner_a.run(runner_a.backup_args(str(source), tags))["ok"] is True

    retention = runner_a.run(
        runner_a.retention_args(tags, {"daily": 1}, host="host-a", dry_run=False)
    )
    assert retention["ok"] is True, retention

    snapshots = runner_a.run(runner_a.snapshots_args(tags))
    assert snapshots["ok"] is True, snapshots
    hosts = {item["hostname"] for item in json.loads(snapshots["stdout"])}
    assert hosts == {"host-a", "host-b"}


def test_local_restic_retention_spans_mutable_tag_changes(tmp_path):
    if not shutil.which("restic"):
        pytest.skip("restic executable is unavailable")

    source = tmp_path / "shared-source"
    source.mkdir()
    (source / "data.txt").write_text("mutable tags\n", encoding="utf-8")
    cfg = Config(config_path=str(_write_local_restic_config(tmp_path)))
    profile = cfg.snapshot_profiles["local-test"]
    profile.repo_homes = []
    profile.include_paths = [str(source)]
    profile.retention = {"path_daily": 1}

    assert snapshot_init(profile)["ok"] is True
    profile.tags = ["owner=before"]
    first_run = snapshot_run(profile)
    assert first_run["success"] is True, first_run
    profile.tags = ["owner=after"]
    second_run = snapshot_run(profile)
    assert second_run["success"] is True, second_run

    snapshots = ResticRunner(profile).run(ResticRunner(profile).snapshots_args())
    assert snapshots["ok"] is True, snapshots
    assert len(json.loads(snapshots["stdout"])) == 1