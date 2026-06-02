"""
Dependency checking and installation.
"""

import subprocess
import sys
import re
import tomllib
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()


def check_system_dependencies() -> Dict[str, Tuple[bool, str]]:
    """
    Check system dependencies.
    
    Returns:
        Dict mapping tool names to (available, message) tuples
    """
    tools = {
        "docker": "Docker container runtime",
        "rsync": "rsync for efficient file copying",
        "tar": "tar for archive operations",
        "rclone": "rclone for Google Drive support (optional)",
    }
    
    results = {}
    for tool, description in tools.items():
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True,
                timeout=2
            )
            available = result.returncode == 0
            if available:
                # Try to get version
                try:
                    version_result = subprocess.run(
                        [tool, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    version = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else ""
                    message = f"{description} - {version}" if version else f"{description} - installed"
                except Exception:
                    message = f"{description} - installed"
            else:
                message = f"{description} - not found"
            results[tool] = (available, message)
        except Exception as e:
            results[tool] = (False, f"{description} - error: {e}")
    
    return results


def check_python_dependencies() -> Tuple[bool, List[str], List[str]]:
    """
    Check Python package dependencies.
    
    Returns:
        Tuple of (all_installed, installed_packages, missing_packages)
    """
    required = {
        "rich": "rich",
        "pyyaml": "yaml",
        "docker": "docker",
        "click": "click",
        "paramiko": "paramiko",
        "cryptography": "cryptography",
        "requests": "requests",
    }
    
    installed = []
    missing = []
    
    for package_name, import_name in required.items():
        try:
            __import__(import_name)
            installed.append(package_name)
        except ImportError:
            missing.append(package_name)
    
    return len(missing) == 0, installed, missing


def _package_name(requirement: str) -> str:
    """Extract a normalized package name from a PEP 508 requirement string."""
    requirement = requirement.split(";", 1)[0].strip()
    requirement = requirement.split("[", 1)[0].strip()
    return re.split(r"[<>=!~]", requirement, maxsplit=1)[0].strip()


def check_project_dependencies() -> List[str]:
    """
    Read runtime dependency names from pyproject.toml.
    
    Returns:
        List of package names from pyproject.toml
    """
    pyproject_file = Path(__file__).parent.parent.parent / "pyproject.toml"
    packages = []
    
    if pyproject_file.exists():
        data = tomllib.loads(pyproject_file.read_text(encoding="utf-8"))
        for dependency in data.get("project", {}).get("dependencies", []):
            package = _package_name(dependency)
            if package:
                packages.append(package)
    
    return packages


def is_venv() -> bool:
    """Return True if running inside a virtual environment."""
    return (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )


def is_externally_managed() -> bool:
    """
    Return True if this Python install is marked as externally managed (PEP 668).

    Modern Debian/Ubuntu ship an EXTERNALLY-MANAGED marker file alongside the
    system Python. We only enable the "do not install here" guard when that
    marker is present so that tests and non-PEP 668 environments can still
    exercise the installer logic.
    """
    try:
        major = sys.version_info.major
        minor = sys.version_info.minor
        candidates = [
            Path(sys.prefix) / "lib" / f"python{major}.{minor}" / "EXTERNALLY-MANAGED",
            Path(sys.prefix) / "EXTERNALLY-MANAGED",
        ]
        return any(p.exists() for p in candidates)
    except Exception:
        return False


def install_python_packages(packages: List[str]) -> bool:
    """
    Install Python packages using uv pip.

    On Ubuntu 22.04+ / Debian 12+ the system Python is externally managed
    (PEP 668) and bare installs are blocked. If we detect an externally
    managed Python and we are not inside a virtual environment, we surface a
    clear message rather than letting pip fail with a confusing error. On
    non-PEP 668 environments we allow the install to proceed (the call is
    typically used from tests or explicit tooling).

    Args:
        packages: List of package names to install

    Returns:
        True if successful
    """
    if is_externally_managed() and not is_venv():
        console.print(
            "[yellow]⚠ package install skipped: the current Python is not inside a "
            "virtual environment.[/yellow]\n"
            "[dim]On Ubuntu 22.04+ / Debian 12+ the system Python is externally "
            "managed (PEP 668).\n"
            "Activate the bbackup venv first:\n"
            "  source .venv/bin/activate\n"
            "then re-run this command.[/dim]"
        )
        return False
    try:
        subprocess.run(
            ["uv", "pip", "install", "--python", sys.executable] + packages,
            check=True,
        )
        return True
    except Exception as exc:
        console.print(
            f"[red]✗ uv pip install failed:[/red] [dim]{exc}[/dim]"
        )
        return False


def check_and_install_dependencies(install_missing: bool = False) -> Dict:
    """
    Check all dependencies and optionally install missing ones.
    
    Args:
        install_missing: If True, prompt to install missing packages
    
    Returns:
        Dict with dependency check results
    """
    # Check system dependencies
    system_deps = check_system_dependencies()
    
    # Check Python dependencies
    all_installed, installed_pkgs, missing_pkgs = check_python_dependencies()
    
    # Check pyproject.toml
    required_pkgs = check_project_dependencies()
    
    results = {
        "system": system_deps,
        "python_installed": installed_pkgs,
        "python_missing": missing_pkgs,
        "python_all_installed": all_installed,
        "required_packages": required_pkgs,
    }
    
    # Install missing packages if requested
    if install_missing and missing_pkgs:
        console.print(f"\n[yellow]Missing Python packages: {', '.join(missing_pkgs)}[/yellow]")
        if Confirm.ask("Install missing packages?", default=True):
            if install_python_packages(missing_pkgs):
                console.print("[green]✓ Packages installed successfully[/green]")
                # Re-check
                all_installed, installed_pkgs, missing_pkgs = check_python_dependencies()
                results["python_installed"] = installed_pkgs
                results["python_missing"] = missing_pkgs
                results["python_all_installed"] = all_installed
            else:
                console.print("[red]✗ Failed to install packages[/red]")
    
    return results


def display_dependency_report(results: Dict):
    """Display dependency check results."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Dependency")
    table.add_column("Status")
    table.add_column("Details")
    
    # System dependencies
    for tool, (available, message) in results["system"].items():
        status = "[green]✓[/green]" if available else "[red]✗[/red]"
        table.add_row(f"System: {tool}", status, message)
    
    # Python dependencies
    if results["python_all_installed"]:
        table.add_row("Python Packages", "[green]✓[/green]", f"All installed ({len(results['python_installed'])})")
    else:
        table.add_row(
            "Python Packages",
            "[red]✗[/red]",
            f"Missing: {', '.join(results['python_missing'])}"
        )
    
    console.print(table)
