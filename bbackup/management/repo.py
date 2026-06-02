"""
Repository URL management with configurable default and override support.

The default URL is the public project repository. Override it via:
  - Environment variable: BBACKUP_REPO_URL
  - Config file:          ~/.config/bbackup/management.yaml → repo_url
  - CLI:                  bbman repo-url --url https://github.com/CruxExperts/best-backup
"""

import os
from pathlib import Path
import yaml

DEFAULT_REPO_URL = "https://github.com/CruxExperts/best-backup"


def get_repo_url() -> str:
    """
    Get repository URL with override priority:
    1. Environment variable BBACKUP_REPO_URL
    2. Config file ~/.config/bbackup/management.yaml → repo_url
    3. Hard-coded default
    
    Returns:
        Repository URL string
    """
    # Check environment variable
    env_url = os.getenv("BBACKUP_REPO_URL")
    if env_url:
        return env_url
    
    # Check config file
    try:
        from .config import get_management_setting
        config_url = get_management_setting("repo_url")
        if config_url:
            return config_url
    except Exception:
        # Fallback to direct file read
        config_path = Path.home() / ".config" / "bbackup" / "management.yaml"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    if config.get("repo_url"):
                        return config["repo_url"]
            except Exception:
                pass  # Fall through to default
    
    # Return hard-coded default
    return DEFAULT_REPO_URL


def set_repo_url(url: str) -> bool:
    """
    Set repository URL override in config file.
    
    Args:
        url: Repository URL to set
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from .config import load_management_config, save_management_config
        config = load_management_config()
        config["repo_url"] = url
        return save_management_config(config)
    except Exception:
        # Fallback to direct file write
        config_path = Path.home() / ".config" / "bbackup" / "management.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new
        config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            except Exception:
                pass
        
        # Update repo_url
        config["repo_url"] = url
        
        # Save config
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            return True
        except Exception:
            return False


def parse_repo_url(url: str) -> dict:
    """
    Parse repository URL to extract owner, repo, and type.
    
    Args:
        url: Repository URL
    
    Returns:
        Dict with keys: type, owner, repo, base_url
    """
    result = {
        "type": "unknown",
        "owner": None,
        "repo": None,
        "base_url": url,
    }
    
    # GitHub
    if "github.com" in url:
        result["type"] = "github"
        parts = url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
        if len(parts) >= 2:
            result["owner"] = parts[0]
            result["repo"] = parts[1].replace(".git", "")
    
    # GitLab
    elif "gitlab.com" in url:
        result["type"] = "gitlab"
        parts = url.replace("https://gitlab.com/", "").replace("http://gitlab.com/", "").split("/")
        if len(parts) >= 2:
            result["owner"] = parts[0]
            result["repo"] = parts[1].replace(".git", "")
    
    # Custom HTTP
    else:
        result["type"] = "custom"
    
    return result
