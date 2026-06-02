"""
Interactive setup wizard for first-time configuration.
"""

import subprocess
import sys
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .first_run import mark_first_run_complete, get_config_file


console = Console()


def check_docker() -> Tuple[bool, str]:
    """Check if Docker is accessible."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, "Docker is accessible"
        else:
            return False, "Docker command failed"
    except FileNotFoundError:
        return False, "Docker not found in PATH"
    except Exception as e:
        return False, f"Docker check error: {e}"


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
            return True, f"{tool} found"
        else:
            return False, f"{tool} not found"
    except Exception:
        return False, f"Could not check {tool}"


def check_python_packages() -> Tuple[bool, List[str]]:
    """Check if required Python packages are installed."""
    required = {
        "rich": "rich",
        "pyyaml": "yaml",
        "docker": "docker",
        "click": "click",
        "paramiko": "paramiko",
        "cryptography": "cryptography",
        "requests": "requests",
    }
    missing = []
    
    for package, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    return len(missing) == 0, missing


def run_setup_wizard() -> bool:
    """
    Run interactive setup wizard.
    
    Returns:
        True if setup completed successfully, False otherwise
    """
    console.print(Panel.fit(
        "[bold cyan]Welcome to bbackup Setup Wizard[/bold cyan]\n\n"
        "This wizard will help you configure bbackup for first-time use.",
        title="Setup"
    ))
    
    checks = []
    
    # Step 1: Check Docker
    console.print("\n[bold]Step 1: Checking Docker access...[/bold]")
    docker_ok, docker_msg = check_docker()
    checks.append(("Docker", docker_ok, docker_msg))
    if docker_ok:
        console.print(f"[green]✓ {docker_msg}[/green]")
    else:
        console.print(f"[yellow]⚠ {docker_msg}[/yellow]")
        if not Confirm.ask("Continue anyway?", default=False):
            return False
    
    # Step 2: Check system tools
    console.print("\n[bold]Step 2: Checking system tools...[/bold]")
    tools = ["rsync", "tar"]
    for tool in tools:
        tool_ok, tool_msg = check_system_tool(tool)
        checks.append((tool, tool_ok, tool_msg))
        if tool_ok:
            console.print(f"[green]✓ {tool_msg}[/green]")
        else:
            console.print(f"[yellow]⚠ {tool_msg}[/yellow]")
    
    # Check optional tools
    rclone_ok, rclone_msg = check_system_tool("rclone")
    if rclone_ok:
        console.print(f"[green]✓ {rclone_msg}[/green]")
    else:
        console.print("[dim]ℹ rclone not found (optional for Google Drive support)[/dim]")
    
    # Step 3: Check Python packages
    console.print("\n[bold]Step 3: Checking Python packages...[/bold]")
    packages_ok, missing = check_python_packages()
    if packages_ok:
        console.print("[green]✓ All required packages installed[/green]")
    else:
        console.print(f"[yellow]⚠ Missing packages: {', '.join(missing)}[/yellow]")
        if Confirm.ask("Install missing packages?", default=True):
            from .dependencies import install_python_packages
            if install_python_packages(missing):
                console.print("[green]✓ Packages installed[/green]")
                packages_ok = True
            else:
                console.print("[red]✗ Failed to install packages[/red]")
                if not Confirm.ask("Continue anyway?", default=False):
                    return False
    
    # Step 4: Create config
    console.print("\n[bold]Step 4: Creating configuration...[/bold]")
    config_file = get_config_file()
    config_dir = config_file.parent
    
    if config_file.exists():
        console.print(f"[yellow]⚠ Config file already exists: {config_file}[/yellow]")
        if not Confirm.ask("Overwrite?", default=False):
            console.print("[dim]Skipping config creation[/dim]")
        else:
            # Initialize config
            try:
                # Call init_config via subprocess to avoid import issues
                subprocess.run(
                    [sys.executable, "-m", "bbackup.cli", "init-config"],
                    check=True
                )
                console.print(f"[green]✓ Config created: {config_file}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed to create config: {e}[/red]")
                return False
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [sys.executable, "-m", "bbackup.cli", "init-config"],
                check=True
            )
            console.print(f"[green]✓ Config created: {config_file}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to create config: {e}[/red]")
            return False
    
    # Step 5: Optional encryption setup
    console.print("\n[bold]Step 5: Encryption setup (optional)...[/bold]")
    if Confirm.ask("Set up encryption keys?", default=False):
        try:
            method = Prompt.ask(
                "Encryption method",
                choices=["symmetric", "asymmetric", "both"],
                default="asymmetric"
            )
            subprocess.run(
                [sys.executable, "-m", "bbackup.cli", "init-encryption", "--method", method],
                check=True
            )
            console.print("[green]✓ Encryption keys created[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Encryption setup failed: {e}[/yellow]")
    
    # Step 6: Summary
    console.print("\n[bold]Step 6: Setup Summary[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    
    for name, ok, msg in checks:
        status = "[green]✓[/green]" if ok else "[yellow]⚠[/yellow]"
        table.add_row(name, status, msg)
    
    console.print(table)
    
    # Mark first run complete
    if mark_first_run_complete():
        console.print("\n[green]✓ Setup completed successfully![/green]")
        console.print("[dim]You can now use 'bbman run' to launch bbackup[/dim]")
        return True
    else:
        console.print("\n[yellow]⚠ Setup completed but failed to mark first run[/yellow]")
        return True  # Still consider it successful
