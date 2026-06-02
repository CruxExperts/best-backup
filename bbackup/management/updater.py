"""
File-level update mechanism with checksum verification.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import requests

from .repo import get_repo_url, parse_repo_url
from .version import check_for_updates


def backup_repository(repo_root: Path, backup_dir: Path) -> bool:
    """
    Backup current repository before update.
    
    Args:
        repo_root: Repository root directory
        backup_dir: Backup directory
    
    Returns:
        True if successful
    """
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy key files/directories
        items_to_backup = [
            "bbackup",
            "bbackup.py",
            "bbman.py",
            "pyproject.toml",
            "uv.lock",
            "config.yaml.example",
        ]
        
        for item in items_to_backup:
            src = repo_root / item
            if src.exists():
                dst = backup_dir / item
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        
        return True
    except Exception:
        return False


def download_file_from_github(repo_url: str, file_path: str, branch: str = "main") -> Optional[bytes]:
    """
    Download file content from GitHub.
    
    Args:
        repo_url: Repository URL
        file_path: File path relative to repo root
        branch: Branch name
    
    Returns:
        File content as bytes, or None if failed
    """
    parsed = parse_repo_url(repo_url)
    if parsed["type"] != "github":
        return None
    
    owner = parsed["owner"]
    repo = parsed["repo"]
    
    # Use raw GitHub URL
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    
    try:
        response = requests.get(raw_url, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    
    return None


def update_file(repo_root: Path, file_path: str, content: bytes, expected_checksum: Optional[str] = None) -> bool:
    """
    Update a single file with content verification.
    
    Args:
        repo_root: Repository root directory
        file_path: File path relative to repo root
        content: File content as bytes
        expected_checksum: Expected SHA-256 checksum (optional)
    
    Returns:
        True if successful
    """
    target_file = repo_root / file_path
    target_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Verify checksum if provided
    if expected_checksum:
        import hashlib
        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != expected_checksum:
            return False
    
    # Write file
    try:
        with open(target_file, 'wb') as f:
            f.write(content)
        return True
    except Exception:
        return False


def update_via_git(repo_root: Path, branch: str = "main") -> bool:
    """
    Update repository using Git pull.
    
    Args:
        repo_root: Repository root directory
        branch: Branch name
    
    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def update_via_download(
    repo_root: Path,
    repo_url: str,
    changed_files: List[str],
    new_files: List[str],
    branch: str = "main"
) -> bool:
    """
    Update repository by downloading changed files.
    
    Args:
        repo_root: Repository root directory
        repo_url: Repository URL
        changed_files: List of changed file paths
        new_files: List of new file paths
        branch: Branch name
    
    Returns:
        True if successful
    """
    parsed = parse_repo_url(repo_url)
    
    all_files = changed_files + new_files
    success_count = 0
    
    for file_path in all_files:
        if parsed["type"] == "github":
            content = download_file_from_github(repo_url, file_path, branch)
            if content:
                if update_file(repo_root, file_path, content):
                    success_count += 1
        # Add support for other repository types as needed
    
    return success_count == len(all_files)


def perform_update(
    repo_root: Path,
    repo_url: Optional[str] = None,
    branch: str = "main",
    method: str = "git"
) -> Dict:
    """
    Perform update operation.
    
    Args:
        repo_root: Repository root directory
        repo_url: Repository URL (uses default if None)
        branch: Branch name
        method: Update method ("git" or "download")
    
    Returns:
        Dict with update results
    """
    if repo_url is None:
        repo_url = get_repo_url()
    
    # Check for updates first
    update_info = check_for_updates(repo_root, repo_url, branch)
    
    if not update_info.get("has_updates"):
        return {
            "success": True,
            "message": "No updates available",
            "files_updated": 0,
        }
    
    # Create backup
    from .first_run import get_data_dir
    backup_dir = get_data_dir() / "backups" / f"pre_update_{int(__import__('time').time())}"
    if not backup_repository(repo_root, backup_dir):
        return {
            "success": False,
            "message": "Failed to create backup",
            "files_updated": 0,
        }
    
    # Perform update
    if method == "git":
        success = update_via_git(repo_root, branch)
        files_updated = len(update_info.get("changed", [])) + len(update_info.get("new", []))
    else:
        success = update_via_download(
            repo_root,
            repo_url,
            update_info.get("changed", []),
            update_info.get("new", []),
            branch
        )
        files_updated = len(update_info.get("changed", [])) + len(update_info.get("new", []))
    
    return {
        "success": success,
        "message": "Update completed" if success else "Update failed",
        "files_updated": files_updated if success else 0,
        "backup_dir": str(backup_dir),
        "changed": update_info.get("changed", []),
        "new": update_info.get("new", []),
        "removed": update_info.get("removed", []),
    }
