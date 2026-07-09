import json
import shutil
import subprocess
import textwrap

import pytest

from bbackup.config import Config
from bbackup.snapshot import (
    load_state,
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
            host_id: test-host
            repository: {tmp_path / "restic-repo"}
            cache_dir: {tmp_path / "cache"}
            state_dir: {tmp_path / "state"}
            password_file: {password_file}
            retry_lock: 1m
            repo_homes:
              - {tmp_path / "repos"}
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
