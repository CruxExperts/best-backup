"""Native restic snapshot support for bbackup."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import socket
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .config import Config, SnapshotProfile


STATE_FILE_NAME = "snapshot-state.json"
STATE_SCHEMA_VERSION = 1


class SnapshotError(RuntimeError):
    """Raised when a snapshot profile cannot be executed safely."""


@dataclass
class DiscoveredRepo:
    path: str
    fingerprint: str
    repo_id: str
    origin: str = ""
    head: str = ""


def expand_path(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_state(profile: SnapshotProfile) -> Dict[str, Any]:
    state_path = state_file(profile)
    if not state_path.exists():
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "profile": profile.name,
            "repos": {},
            "alerts": [],
        }
    with state_path.open("r", encoding="utf-8") as f:
        state = json.load(f) or {}
    state.setdefault("schema_version", STATE_SCHEMA_VERSION)
    state.setdefault("profile", profile.name)
    state.setdefault("repos", {})
    state.setdefault("alerts", [])
    return state


def save_state(profile: SnapshotProfile, state: Dict[str, Any]) -> None:
    state_path = state_file(profile)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp_path.replace(state_path)


def state_file(profile: SnapshotProfile) -> Path:
    state_dir = profile.state_dir or f"~/.local/state/bbackup/{profile.host_id or socket.gethostname()}/{profile.name}"
    return expand_path(state_dir) / STATE_FILE_NAME


def _git(path: Path, args: List[str]) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _repo_from_path(path: Path) -> Optional[DiscoveredRepo]:
    toplevel = _git(path, ["rev-parse", "--show-toplevel"])
    if not toplevel:
        return None
    root = Path(toplevel).resolve()
    if root != path.resolve():
        return None
    origin = _git(root, ["config", "--get", "remote.origin.url"]) or ""
    head = _git(root, ["rev-parse", "HEAD"]) or ""
    git_dir = _git(root, ["rev-parse", "--git-dir"]) or ""
    fingerprint_source = "\n".join([str(root), origin, head, git_dir])
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
    repo_id = hashlib.sha256(f"{origin or root}:{fingerprint}".encode("utf-8")).hexdigest()[:16]
    return DiscoveredRepo(
        path=str(root),
        fingerprint=fingerprint,
        repo_id=repo_id,
        origin=origin,
        head=head,
    )


def discover_git_repos(profile: SnapshotProfile) -> List[DiscoveredRepo]:
    """Discover immediate child Git roots under repo homes plus explicit roots."""
    repos: Dict[str, DiscoveredRepo] = {}
    for home in profile.repo_homes:
        home_path = expand_path(home)
        if not home_path.is_dir():
            continue
        for child in sorted(home_path.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            repo = _repo_from_path(child)
            if repo:
                repos[repo.path] = repo
    for explicit in profile.explicit_repos:
        path = expand_path(explicit)
        repo = _repo_from_path(path)
        if repo:
            repos[repo.path] = repo
    return list(repos.values())


def reconcile_repos(profile: SnapshotProfile, discovered: List[DiscoveredRepo]) -> Dict[str, Any]:
    state = load_state(profile)
    repos = state.setdefault("repos", {})
    alerts: List[Dict[str, str]] = []
    now = utc_now()
    discovered_by_path = {repo.path: repo for repo in discovered}

    for repo in discovered:
        reused = [
            data for data in repos.values()
            if data.get("path") == repo.path
            and data.get("fingerprint") != repo.fingerprint
        ]
        if reused:
            alerts.append({
                "severity": "critical",
                "code": "path_reuse_conflict",
                "path": repo.path,
                "message": f"Retired repo path reused with a different Git fingerprint: {repo.path}",
            })
            continue

        entry = repos.setdefault(repo.repo_id, {})
        entry.update({
            "repo_id": repo.repo_id,
            "path": repo.path,
            "fingerprint": repo.fingerprint,
            "origin": repo.origin,
            "head": repo.head,
            "status": "active",
            "last_seen_at": now,
        })
        entry.setdefault("first_seen_at", now)
        entry.setdefault("successful_snapshot_ids", [])

    for repo_id, entry in repos.items():
        if entry.get("status") != "active":
            continue
        if entry.get("path") in discovered_by_path:
            continue
        if entry.get("successful_snapshot_ids"):
            entry["status"] = "retired"
            entry["retired_at"] = now
        else:
            alerts.append({
                "severity": "critical",
                "code": "missing_without_snapshot",
                "path": entry.get("path", ""),
                "repo_id": repo_id,
                "message": f"Repo disappeared before any successful snapshot: {entry.get('path', repo_id)}",
            })

    state["alerts"] = alerts
    save_state(profile, state)
    return {
        "profile": profile.name,
        "state_file": str(state_file(profile)),
        "discovered_repos": [repo.__dict__ for repo in discovered],
        "active_repo_ids": sorted(
            repo_id for repo_id, entry in repos.items() if entry.get("status") == "active"
        ),
        "retired_repo_ids": sorted(
            repo_id for repo_id, entry in repos.items() if entry.get("status") == "retired"
        ),
        "alerts": alerts,
    }


class ResticRunner:
    def __init__(self, profile: SnapshotProfile):
        if profile.engine != "restic":
            raise SnapshotError(f"Unsupported snapshot engine: {profile.engine}")
        self.profile = profile

    def env(self) -> Dict[str, str]:
        env = dict(os.environ)
        if self.profile.cache_dir:
            env["RESTIC_CACHE_DIR"] = str(expand_path(self.profile.cache_dir))
        return env

    def base_args(self) -> List[str]:
        args = ["restic", "-r", self.profile.repository]
        if self.profile.password_file:
            args.extend(["--password-file", str(expand_path(self.profile.password_file))])
        if self.profile.cache_dir:
            args.extend(["--cache-dir", str(expand_path(self.profile.cache_dir))])
        args.extend(["--json", "--retry-lock", self.profile.retry_lock])
        return args

    def init_args(self) -> List[str]:
        return [*self.base_args(), "init"]

    def snapshots_args(self, tags: Optional[Iterable[str]] = None) -> List[str]:
        args = [*self.base_args(), "snapshots"]
        for tag in tags or []:
            args.extend(["--tag", tag])
        return args

    def check_args(self, read_data_subset: Optional[str] = None) -> List[str]:
        args = [*self.base_args(), "check"]
        if read_data_subset:
            args.extend(["--read-data-subset", read_data_subset])
        return args

    def backup_args(self, path: str, tags: Iterable[str]) -> List[str]:
        args = [*self.base_args(), "backup", str(expand_path(path))]
        if self.profile.host_id:
            args.extend(["--host", self.profile.host_id])
        for tag in tags:
            args.extend(["--tag", tag])
        for exclude in self.profile.exclude_paths:
            args.extend(["--exclude", exclude])
        return args

    def restore_args(self, snapshot_id: str, target: str, include: Optional[str] = None) -> List[str]:
        args = [*self.base_args(), "restore", snapshot_id, "--target", str(expand_path(target))]
        if include:
            args.extend(["--include", include])
        return args

    def forget_args(self, tags: Iterable[str], dry_run: bool = True) -> List[str]:
        args = [*self.base_args(), "forget"]
        if dry_run:
            args.append("--dry-run")
        for tag in tags:
            args.extend(["--tag", tag])
        return args

    def run(self, args: List[str]) -> Dict[str, Any]:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            env=self.env(),
            check=False,
        )
        return {
            "args": args,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "ok": result.returncode == 0,
        }


def common_tags(profile: SnapshotProfile, scope: str, extra: Iterable[str] = ()) -> List[str]:
    return [
        "bbackup",
        f"profile={profile.name}",
        f"scope={scope}",
        *profile.tags,
        *list(extra),
    ]


def snapshot_plan(profile: SnapshotProfile) -> Dict[str, Any]:
    discovered = discover_git_repos(profile)
    reconcile = reconcile_repos(profile, discovered)
    runner = ResticRunner(profile)
    repo_commands = [
        {
            "repo_id": repo.repo_id,
            "path": repo.path,
            "args": runner.backup_args(
                repo.path,
                common_tags(profile, "repo", [f"repo_id={repo.repo_id}"]),
            ),
        }
        for repo in discovered
        if repo.repo_id in set(reconcile["active_repo_ids"])
    ]
    include_commands = [
        {
            "path": str(expand_path(path)),
            "args": runner.backup_args(path, common_tags(profile, "path", [f"path_id={path_id(path)}"])),
        }
        for path in profile.include_paths
    ]
    return {
        "profile": profile.name,
        "repository": profile.repository,
        "host_id": profile.host_id,
        "state_file": reconcile["state_file"],
        "repos": repo_commands,
        "paths": include_commands,
        "alerts": reconcile["alerts"],
    }


def path_id(path: str) -> str:
    return hashlib.sha256(str(expand_path(path)).encode("utf-8")).hexdigest()[:16]


def mark_snapshot_success(profile: SnapshotProfile, repo_id: str, snapshot_id: str) -> None:
    state = load_state(profile)
    entry = state.setdefault("repos", {}).setdefault(repo_id, {})
    snapshots = entry.setdefault("successful_snapshot_ids", [])
    if snapshot_id and snapshot_id not in snapshots:
        snapshots.append(snapshot_id)
    entry["last_successful_snapshot_id"] = snapshot_id
    entry["last_successful_snapshot_at"] = utc_now()
    save_state(profile, state)


def snapshot_init(profile: SnapshotProfile, dry_run: bool = False) -> Dict[str, Any]:
    runner = ResticRunner(profile)
    args = runner.init_args()
    if dry_run:
        return {"dry_run": True, "args": args}
    if profile.cache_dir:
        expand_path(profile.cache_dir).mkdir(parents=True, exist_ok=True)
    expand_path(profile.state_dir).mkdir(parents=True, exist_ok=True)
    return runner.run(args)


def snapshot_run(profile: SnapshotProfile, dry_run: bool = False) -> Dict[str, Any]:
    plan = snapshot_plan(profile)
    if dry_run:
        plan["dry_run"] = True
        return plan
    if plan["alerts"]:
        raise SnapshotError("Refusing to run snapshot profile with critical alerts")
    runner = ResticRunner(profile)
    results = []
    for item in [*plan["repos"], *plan["paths"]]:
        result = runner.run(item["args"])
        result["target"] = item.get("path")
        result["repo_id"] = item.get("repo_id")
        results.append(result)
        if item.get("repo_id") and result["ok"]:
            snapshot_id = _extract_snapshot_id(result["stdout"])
            if snapshot_id:
                mark_snapshot_success(profile, item["repo_id"], snapshot_id)
    return {"profile": profile.name, "results": results, "success": all(r["ok"] for r in results)}


def _extract_snapshot_id(stdout: str) -> str:
    for line in stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("message_type") == "summary":
            return obj.get("snapshot_id", "")
    return ""


def snapshot_check(profile: SnapshotProfile, read_data_subset: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    runner = ResticRunner(profile)
    args = runner.check_args(read_data_subset)
    if dry_run:
        return {"dry_run": True, "args": args}
    return runner.run(args)


def snapshot_restore(
    profile: SnapshotProfile,
    snapshot_id: str,
    target: str,
    include: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    runner = ResticRunner(profile)
    args = runner.restore_args(snapshot_id, target, include)
    if dry_run:
        return {"dry_run": True, "args": args}
    return runner.run(args)


def retire_repo(profile: SnapshotProfile, repo_id: str) -> Dict[str, Any]:
    state = load_state(profile)
    entry = state.get("repos", {}).get(repo_id)
    if not entry:
        raise SnapshotError(f"Unknown repo_id: {repo_id}")
    if not entry.get("successful_snapshot_ids"):
        raise SnapshotError(f"Cannot retire repo without a successful snapshot: {repo_id}")
    entry["status"] = "retired"
    entry["retired_at"] = utc_now()
    save_state(profile, state)
    return {"repo_id": repo_id, "status": "retired", "state_file": str(state_file(profile))}


def purge_plan(profile: SnapshotProfile, repo_id: str) -> Dict[str, Any]:
    state = load_state(profile)
    entry = state.get("repos", {}).get(repo_id)
    if not entry:
        raise SnapshotError(f"Unknown repo_id: {repo_id}")
    if entry.get("status") == "active":
        raise SnapshotError(f"Refusing to purge active repo_id: {repo_id}")
    runner = ResticRunner(profile)
    tags = common_tags(profile, "repo", [f"repo_id={repo_id}"])
    return {
        "repo_id": repo_id,
        "status": entry.get("status"),
        "path": entry.get("path"),
        "dry_run_required": True,
        "forget_args": runner.forget_args(tags, dry_run=True),
        "destructive_args_after_confirmation": runner.forget_args(tags, dry_run=False),
    }


def schedule_units(profile: SnapshotProfile) -> Dict[str, str]:
    service_name = f"bbackup-{profile.host_id.lower()}-{profile.name}"
    schedule = profile.schedule or {}
    daily_time = schedule.get("daily_time", "03:30")
    maintenance_time = schedule.get("maintenance_time", "Sun 04:30")
    verification_time = schedule.get("verification_time", "monthly")
    unit = f"""[Unit]
Description=bbackup {profile.host_id} {profile.name} snapshot

[Service]
Type=oneshot
ExecStart=bbackup snapshot run --profile {shlex.quote(profile.name)}
"""
    timer = f"""[Unit]
Description=Run bbackup {profile.host_id} {profile.name} snapshot daily

[Timer]
OnCalendar=*-*-* {daily_time}:00
Persistent=true
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target
"""
    maintenance = f"""[Unit]
Description=bbackup {profile.host_id} {profile.name} weekly maintenance

[Timer]
OnCalendar={maintenance_time}
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
"""
    verification = f"""[Unit]
Description=bbackup {profile.host_id} {profile.name} monthly verification

[Timer]
OnCalendar={verification_time}
Persistent=true
RandomizedDelaySec=2h

[Install]
WantedBy=timers.target
"""
    return {
        f"{service_name}.service": unit,
        f"{service_name}.timer": timer,
        f"{service_name}-maintenance.timer": maintenance,
        f"{service_name}-verification.timer": verification,
    }


def check_snapshot_profile(profile: SnapshotProfile) -> Dict[str, Any]:
    checks: Dict[str, Dict[str, Any]] = {}
    checks["engine"] = {"ok": profile.engine == "restic", "message": profile.engine}
    checks["restic"] = _tool_check("restic")
    checks["rclone"] = _tool_check("rclone") if profile.repository.startswith("rclone:") else {
        "ok": True,
        "message": "not required for non-rclone repository",
    }
    checks["repository"] = {"ok": bool(profile.repository), "message": profile.repository or "missing"}
    checks["hostname"] = _hostname_check(profile)
    checks["password_file"] = _password_file_check(profile)
    checks["cache_dir"] = _dir_check(profile.cache_dir, create=False)
    checks["state_dir"] = _dir_check(profile.state_dir, create=False)
    checks["repository_initialized"] = _repository_initialized_check(profile)
    ok = all(check["ok"] for check in checks.values())
    return {"ok": ok, "profile": profile.name, "checks": checks}


def check_all_snapshot_profiles(config: Config) -> Dict[str, Any]:
    profiles = {
        name: check_snapshot_profile(profile)
        for name, profile in config.snapshot_profiles.items()
    }
    return {
        "ok": all(item["ok"] for item in profiles.values()) if profiles else True,
        "profiles": profiles,
    }


def _tool_check(name: str) -> Dict[str, Any]:
    found = shutil.which(name)
    if not found:
        return {"ok": False, "message": f"{name} not found in PATH"}
    try:
        result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
        version = result.stdout.splitlines()[0] if result.stdout else found
    except (OSError, subprocess.TimeoutExpired):
        version = found
    return {"ok": True, "message": version}


def _hostname_check(profile: SnapshotProfile) -> Dict[str, Any]:
    if not profile.host_id:
        return {"ok": False, "message": "host_id missing"}
    actual = socket.gethostname()
    if profile.host_id.lower() == actual.lower():
        return {"ok": True, "message": actual}
    return {"ok": False, "message": f"profile host_id {profile.host_id} does not match hostname {actual}"}


def _password_file_check(profile: SnapshotProfile) -> Dict[str, Any]:
    if not profile.password_file:
        return {"ok": False, "message": "password_file missing"}
    path = expand_path(profile.password_file)
    if not path.exists():
        return {"ok": False, "message": f"password file not found: {path}"}
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return {"ok": False, "message": f"password file must not be group/world accessible: {oct(mode)}"}
    return {"ok": True, "message": str(path)}


def _dir_check(path: str, create: bool = False) -> Dict[str, Any]:
    if not path:
        return {"ok": False, "message": "missing"}
    resolved = expand_path(path)
    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.exists():
        return {"ok": False, "message": f"not found: {resolved}"}
    if not os.access(resolved, os.W_OK):
        return {"ok": False, "message": f"not writable: {resolved}"}
    return {"ok": True, "message": str(resolved)}


def _repository_initialized_check(profile: SnapshotProfile) -> Dict[str, Any]:
    if not shutil.which("restic") or not profile.repository:
        return {"ok": False, "message": "restic or repository missing"}
    runner = ResticRunner(profile)
    result = runner.run(runner.snapshots_args(["bbackup"]))
    if result["ok"]:
        return {"ok": True, "message": "repository accessible"}
    return {"ok": False, "message": result["stderr"] or result["stdout"] or "repository inaccessible"}
