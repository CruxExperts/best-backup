"""
Comprehensive health check system.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import docker

from rich.console import Console
from rich.table import Table

from ..config import Config
from ..snapshot import check_all_snapshot_profiles
from .dependencies import check_python_dependencies as _check_python_dependencies

console = Console()


def check_docker() -> Tuple[bool, str]:
    """Check Docker daemon accessibility."""
    try:
        client = docker.from_env()
        client.ping()
        version = client.version()
        return True, f"Docker {version.get('Version', 'unknown')} accessible"
    except docker.errors.DockerException as e:
        return False, f"Docker not accessible: {e}"
    except Exception as e:
        return False, f"Docker check error: {e}"


def check_docker_socket() -> Tuple[bool, str]:
    """Check Docker socket permissions."""
    socket_path = Path("/var/run/docker.sock")
    if not socket_path.exists():
        return False, "Docker socket not found"
    
    if os.access(socket_path, os.R_OK | os.W_OK):
        return True, "Docker socket accessible"
    else:
        return False, "Docker socket permission denied (add user to docker group)"


def check_system_tool(tool: str) -> Tuple[bool, str]:
    """Check if a system tool is available."""
    try:
        result = subprocess.run(
            ["which", tool],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # Get version if possible
            try:
                version_result = subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else ""
                return True, f"{tool} found" + (f" ({version})" if version else "")
            except Exception:
                return True, f"{tool} found"
        else:
            return False, f"{tool} not found in PATH"
    except Exception as e:
        return False, f"Could not check {tool}: {e}"


def check_python_packages() -> Tuple[bool, List[str], List[str]]:
    """Check required Python package imports and security version floors."""
    return _check_python_dependencies()


def check_config_file() -> Tuple[bool, str]:
    """Check if config file exists and is valid."""
    config_path = Path.home() / ".config" / "bbackup" / "config.yaml"
    
    if not config_path.exists():
        return False, "Config file not found"
    
    try:
        Config(config_path=str(config_path))
        return True, f"Config file valid: {config_path}"
    except Exception as e:
        return False, f"Config file invalid: {e}"


def check_directories() -> Tuple[bool, List[str]]:
    """Check directory permissions."""
    issues = []
    
    # Check staging directory
    try:
        config = Config()
        staging = Path(config.get_staging_dir()).expanduser()
        staging.mkdir(parents=True, exist_ok=True)
        if not os.access(staging, os.W_OK):
            issues.append(f"Staging directory not writable: {staging}")
    except Exception as e:
        issues.append(f"Staging directory error: {e}")
    
    # Check log directory
    try:
        config = Config()
        log_file = config.data.get('logging', {}).get('file', '~/.local/share/bbackup/bbackup.log')
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(log_path.parent, os.W_OK):
            issues.append(f"Log directory not writable: {log_path.parent}")
    except Exception as e:
        issues.append(f"Log directory error: {e}")
    
    return len(issues) == 0, issues


def run_health_check() -> Dict:
    """
    Run comprehensive health check.
    
    Returns:
        Dict with health check results
    """
    config_error = ""
    try:
        config = Config()
        snapshot_profiles = check_all_snapshot_profiles(config)
    except Exception as exc:
        config = None
        config_error = str(exc)
        snapshot_profiles = {
            "ok": False,
            "profiles": {},
            "error": f"Could not load config for snapshot health checks: {exc}",
        }
    results = {
        "docker": check_docker(),
        "docker_socket": check_docker_socket(),
        "rsync": check_system_tool("rsync"),
        "tar": check_system_tool("tar"),
        "rclone": check_system_tool("rclone"),  # Optional
        "python_packages": check_python_packages(),
        "config": check_config_file(),
        "directories": check_directories(),
        "snapshot_profiles": snapshot_profiles,
    }
    if config_error and results["config"][0]:
        results["config"] = (False, f"Config file invalid: {config_error}")
    
    # Calculate overall health
    critical_checks = [
        results["docker"][0],
        results["docker_socket"][0],
        results["rsync"][0],
        results["tar"][0],
        results["python_packages"][0],
    ]
    
    snapshot_ok = results["snapshot_profiles"]["ok"]
    all_critical_ok = all(critical_checks) and snapshot_ok
    overall_health = "healthy" if all_critical_ok else "unhealthy"
    
    results["overall"] = overall_health
    results["all_critical_ok"] = all_critical_ok
    
    return results


def display_health_report(results: Dict):
    """Display health check results in a formatted table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    
    # Critical checks
    checks = [
        ("Docker Daemon", results["docker"]),
        ("Docker Socket", results["docker_socket"]),
        ("rsync", results["rsync"]),
        ("tar", results["tar"]),
        ("Config File", results["config"]),
    ]
    
    for name, (ok, msg) in checks:
        status = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(name, status, msg)
    
    # Python packages (special handling - returns 3 values)
    pkg_all_ok, pkg_installed, pkg_missing = results["python_packages"]
    if pkg_all_ok:
        table.add_row("Python Packages", "[green]✓[/green]", f"All installed ({len(pkg_installed)})")
    else:
        table.add_row("Python Packages", "[red]✗[/red]", f"Missing: {', '.join(pkg_missing)}")
    
    # Optional checks
    rclone_ok, rclone_msg = results["rclone"]
    if rclone_ok:
        table.add_row("rclone (optional)", "[green]✓[/green]", rclone_msg)
    else:
        table.add_row("rclone (optional)", "[dim]○[/dim]", "[dim]Not required[/dim]")
    
    # Directory checks
    dirs_ok, dir_issues = results["directories"]
    if dirs_ok:
        table.add_row("Directories", "[green]✓[/green]", "All directories accessible")
    else:
        for issue in dir_issues:
            table.add_row("Directories", "[yellow]⚠[/yellow]", issue)

    # Snapshot profile checks
    snapshot_profiles = results.get("snapshot_profiles", {}).get("profiles", {})
    for profile_name, profile_result in snapshot_profiles.items():
        status = "[green]✓[/green]" if profile_result.get("ok") else "[red]✗[/red]"
        failed = [
            name for name, check in profile_result.get("checks", {}).items()
            if not check.get("ok")
        ]
        detail = "ready" if not failed else f"failed: {', '.join(failed)}"
        table.add_row(f"Snapshot profile: {profile_name}", status, detail)
    
    console.print(table)
    
    # Overall status
    if results["overall"] == "healthy":
        console.print("\n[green]✓ System is healthy[/green]")
    else:
        console.print("\n[red]✗ System has issues - please fix critical items above[/red]")


def generate_health_report(results: Dict) -> str:
    """Generate text health report."""
    report = []
    report.append("bbackup Health Check Report")
    report.append("=" * 50)
    report.append("")
    
    for check_name, result in [
        ("Docker Daemon", results["docker"]),
        ("Docker Socket", results["docker_socket"]),
        ("rsync", results["rsync"]),
        ("tar", results["tar"]),
        ("Python Packages", results["python_packages"]),
        ("Config File", results["config"]),
    ]:
        ok = result[0]
        if check_name == "Python Packages":
            _, installed, missing = result
            msg = f"All installed ({len(installed)})" if ok else f"Missing: {', '.join(missing)}"
        else:
            msg = result[1]
        status = "✓" if ok else "✗"
        report.append(f"{status} {check_name}: {msg}")

    snapshot_profiles = results.get("snapshot_profiles", {}).get("profiles", {})
    for profile_name, profile_result in snapshot_profiles.items():
        status = "✓" if profile_result.get("ok") else "✗"
        report.append(f"{status} Snapshot profile {profile_name}: {'ready' if profile_result.get('ok') else 'not ready'}")
    
    report.append("")
    report.append(f"Overall Status: {results['overall'].upper()}")
    
    return "\n".join(report)
