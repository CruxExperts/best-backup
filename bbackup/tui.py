"""
Rich TUI interface for bbackup.
Provides BTOP-like graphical interface for backup operations with live updates.
"""

import time
import threading
from typing import Any, List, Dict, Optional, Set, Callable
from datetime import timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, 
    TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
)
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Confirm, Prompt
from rich import box

from . import __version__
from .config import Config, BackupSet


class BackupStatus:
    """Thread-safe status tracker for backup operations."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.current_action = "Initializing..."
        self.current_item = ""
        self.total_items = 0
        self.completed_items = 0
        self.start_time = None
        self.eta = None
        self.errors = []
        self.warnings = []
        self.status = "idle"  # idle, running, paused, cancelled, completed, error
        self.containers_status = {}
        self.volumes_status = {}
        self.networks_status = {}
        self.filesystems_status: Dict[str, Any] = {}
        self.remote_status = {}
        self.skip_current = False  # Flag to skip current item
        self.encryption_status = "idle"  # idle, encrypting, encrypted, failed
        
        # Transfer metrics
        self.bytes_transferred = 0  # Total bytes transferred
        self.total_bytes = 0  # Total bytes to transfer (if known)
        self.transfer_speed = 0.0  # Current transfer speed in MB/s
        self.files_transferred = 0  # Number of files transferred
        self.total_files = 0  # Total files to transfer (if known)
        self.current_file = ""  # Current file being processed
        self.last_update_time = None  # For speed calculation
        self.last_bytes = 0  # For speed calculation
    
    def update(self, action: str = None, item: str = None, 
               completed: int = None, total: int = None,
               bytes_transferred: int = None, total_bytes: int = None,
               files_transferred: int = None, total_files: int = None,
               current_file: str = None):
        """Update status (thread-safe)."""
        with self.lock:
            if action:
                self.current_action = action
            if item:
                self.current_item = item
            if completed is not None:
                self.completed_items = completed
            if total is not None:
                self.total_items = total
            if bytes_transferred is not None:
                self.bytes_transferred = bytes_transferred
            if total_bytes is not None:
                self.total_bytes = total_bytes
            if files_transferred is not None:
                self.files_transferred = files_transferred
            if total_files is not None:
                self.total_files = total_files
            if current_file is not None:
                self.current_file = current_file
            
            # Calculate transfer speed
            current_time = time.time()
            if self.last_update_time and self.bytes_transferred > self.last_bytes:
                time_delta = current_time - self.last_update_time
                bytes_delta = self.bytes_transferred - self.last_bytes
                if time_delta > 0:
                    # Calculate speed in MB/s
                    self.transfer_speed = (bytes_delta / time_delta) / (1024 * 1024)
            self.last_update_time = current_time
            self.last_bytes = self.bytes_transferred
            
            # Calculate ETA
            if self.start_time and self.completed_items > 0 and self.total_items > 0:
                elapsed = time.time() - self.start_time
                rate = self.completed_items / elapsed
                remaining = self.total_items - self.completed_items
                if rate > 0:
                    self.eta = timedelta(seconds=int(remaining / rate))
                else:
                    self.eta = None
            # Also calculate ETA based on transfer speed if we have bytes info
            elif self.transfer_speed > 0 and self.total_bytes > 0 and self.bytes_transferred < self.total_bytes:
                remaining_bytes = self.total_bytes - self.bytes_transferred
                remaining_seconds = remaining_bytes / (self.transfer_speed * 1024 * 1024)
                if remaining_seconds > 0:
                    self.eta = timedelta(seconds=int(remaining_seconds))
    
    def start(self):
        """Start timing."""
        with self.lock:
            self.start_time = time.time()
            self.status = "running"
    
    def cancel(self):
        """Cancel operation."""
        with self.lock:
            self.status = "cancelled"
    
    def add_error(self, error: str):
        """Add error message."""
        with self.lock:
            self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add warning message."""
        with self.lock:
            self.warnings.append(warning)


class BackupTUI:
    """Terminal UI for backup operations with BTOP-like interface."""
    
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.status = BackupStatus()
        self.cancelled = False
    
    def show_header(self, title: str = "bbackup - Docker Backup Tool"):
        """Display header panel."""
        header = Panel(
            f"[bold cyan]{title}[/bold cyan]\n"
            f"[dim]Version {__version__} - Docker Backup & Restore[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
        )
        self.console.print(header)
    
    def create_live_dashboard(self) -> Layout:
        """Create live-updating dashboard layout (BTOP-like)."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main", ratio=2),
            Layout(name="progress", size=8),
            Layout(name="status", size=6),
            Layout(name="footer", size=3),
        )
        
        layout["main"].split_row(
            Layout(name="containers", ratio=1),
            Layout(name="volumes", ratio=1),
            Layout(name="filesystems", ratio=1),
        )
        
        # Header
        elapsed = ""
        if self.status.start_time:
            elapsed_seconds = int(time.time() - self.status.start_time)
            elapsed = f" | Elapsed: {timedelta(seconds=elapsed_seconds)}"
        
        eta_str = ""
        if self.status.eta:
            eta_str = f" | ETA: {self.status.eta}"
        
        status_color = {
            "idle": "yellow",
            "running": "green",
            "paused": "yellow",
            "cancelled": "red",
            "completed": "green",
            "error": "red",
        }.get(self.status.status, "white")
        
        # Transfer speed display
        speed_str = ""
        if self.status.transfer_speed > 0:
            if self.status.transfer_speed >= 1024:
                speed_str = f" | Speed: {self.status.transfer_speed/1024:.2f} GB/s"
            else:
                speed_str = f" | Speed: {self.status.transfer_speed:.2f} MB/s"
        
        # Bytes transferred display
        bytes_str = ""
        if self.status.bytes_transferred > 0:
            if self.status.bytes_transferred >= 1024**3:
                bytes_str = f" | Transferred: {self.status.bytes_transferred/(1024**3):.2f} GB"
            elif self.status.bytes_transferred >= 1024**2:
                bytes_str = f" | Transferred: {self.status.bytes_transferred/(1024**2):.2f} MB"
            else:
                bytes_str = f" | Transferred: {self.status.bytes_transferred/1024:.2f} KB"
        
        # Files transferred display
        files_str = ""
        if self.status.files_transferred > 0:
            if self.status.total_files > 0:
                files_str = f" | Files: {self.status.files_transferred}/{self.status.total_files}"
            else:
                files_str = f" | Files: {self.status.files_transferred}"
        
        header_content = f"""
[bold cyan]bbackup[/bold cyan] - Docker Backup Tool  [dim]v{__version__}[/dim]
Status: [{status_color}]{self.status.status.upper()}[/{status_color}]{elapsed}{eta_str}{speed_str}{bytes_str}{files_str}

[bold]Current:[/bold] {self.status.current_action}
[bold]Item:[/bold] {self.status.current_item if self.status.current_item else 'N/A'}
{('[bold]File:[/bold] ' + self.status.current_file[:60]) if self.status.current_file else ''}
"""
        layout["header"].update(Panel(header_content.strip(), border_style="cyan", box=box.ROUNDED))
        
        # Progress bar with enhanced metrics
        # Use bytes-based progress if available, otherwise use item-based
        if self.status.total_bytes > 0:
            # Bytes-based progress (more accurate for file transfers)
            progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.completed:>10}[/cyan]/[dim]{task.total:>10}[/dim]"),
                TextColumn("[dim]bytes[/dim]"),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
            )
            total = self.status.total_bytes
            completed = self.status.bytes_transferred
        else:
            # Item-based progress (fallback)
            progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                MofNCompleteColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
            )
            
            # Add TimeRemainingColumn only if we have progress
            if self.status.total_items > 0 and self.status.completed_items > 0:
                progress_bar.columns = (
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=40),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("•"),
                    MofNCompleteColumn(),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    TextColumn("•"),
                    TimeRemainingColumn(),
                )
            total = self.status.total_items if self.status.total_items > 0 else None
            completed = self.status.completed_items
        
        progress_bar.add_task(
            self.status.current_action[:50] if self.status.current_action else "Processing...",
            total=total,
            completed=completed,
        )
        
        layout["progress"].update(
            Panel(progress_bar, title="Progress", border_style="blue", box=box.ROUNDED)
        )
        
        # Containers panel with enhanced info
        containers_table = Table(show_header=True, box=box.SIMPLE, show_edge=False)
        containers_table.add_column("Container", style="cyan", width=22)
        containers_table.add_column("Status", width=10)
        containers_table.add_column("Progress", style="dim", width=12)
        
        for name, status_info in list(self.status.containers_status.items())[:10]:
            # Handle both dict and string status
            if isinstance(status_info, dict):
                status = status_info.get("status", "unknown")
                size = status_info.get("size", "-")
                speed = status_info.get("speed", "")
            else:
                status = status_info
                size = "-"
                speed = ""
            
            status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"
            progress_display = size if size != "-" else speed if speed else status
            containers_table.add_row(
                name[:22],
                f"[{status_color}]{status[:8]}[/{status_color}]",
                progress_display[:12],
            )
        
        if len(self.status.containers_status) == 0:
            containers_table.add_row("[dim]No containers backed up yet[/dim]", "", "")
        
        layout["containers"].update(
            Panel(containers_table, title="Containers", border_style="green", box=box.ROUNDED)
        )
        
        # Volumes panel with enhanced info
        volumes_table = Table(show_header=True, box=box.SIMPLE, show_edge=False)
        volumes_table.add_column("Volume", style="cyan", width=22)
        volumes_table.add_column("Status", width=10)
        volumes_table.add_column("Progress", style="dim", width=12)
        
        for name, status_info in list(self.status.volumes_status.items())[:10]:
            # Handle both dict and string status
            if isinstance(status_info, dict):
                status = status_info.get("status", "unknown")
                size = status_info.get("size", "-")
                speed = status_info.get("speed", "")
            else:
                status = status_info
                size = "-"
                speed = ""
            
            status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"
            progress_display = size if size != "-" else speed if speed else status
            volumes_table.add_row(
                name[:22],
                f"[{status_color}]{status[:8]}[/{status_color}]",
                progress_display[:12],
            )
        
        if len(self.status.volumes_status) == 0:
            volumes_table.add_row("[dim]No volumes backed up yet[/dim]", "", "")
        
        layout["volumes"].update(
            Panel(volumes_table, title="Volumes", border_style="yellow", box=box.ROUNDED)
        )

        # Filesystems panel
        filesystems_table = Table(show_header=True, box=box.SIMPLE, show_edge=False)
        filesystems_table.add_column("Path", style="cyan", width=22)
        filesystems_table.add_column("Status", width=10)
        filesystems_table.add_column("Progress", style="dim", width=12)

        for name, status_info in list(self.status.filesystems_status.items())[:10]:
            if isinstance(status_info, dict):
                fs_status = status_info.get("status", "unknown")
                size = status_info.get("size", "-")
                speed = status_info.get("speed", "")
            else:
                fs_status = status_info
                size = "-"
                speed = ""
            color = "green" if fs_status == "success" else "red" if fs_status == "failed" else "yellow"
            progress_display = size if size != "-" else speed if speed else fs_status
            filesystems_table.add_row(
                name[:22],
                f"[{color}]{fs_status[:8]}[/{color}]",
                progress_display[:12],
            )

        if not self.status.filesystems_status:
            filesystems_table.add_row("[dim]No paths backed up yet[/dim]", "", "")

        layout["filesystems"].update(
            Panel(filesystems_table, title="Filesystems", border_style="cyan", box=box.ROUNDED)
        )

        # Status panel with encryption info and metrics
        status_lines = []
        
        # Show transfer metrics if available
        if self.status.transfer_speed > 0:
            if self.status.transfer_speed >= 1024:
                speed_display = f"{self.status.transfer_speed/1024:.2f} GB/s"
            else:
                speed_display = f"{self.status.transfer_speed:.2f} MB/s"
            status_lines.append(f"[cyan]⚡ Transfer Speed:[/cyan] {speed_display}")
        
        if self.status.bytes_transferred > 0:
            if self.status.bytes_transferred >= 1024**3:
                bytes_display = f"{self.status.bytes_transferred/(1024**3):.2f} GB"
            elif self.status.bytes_transferred >= 1024**2:
                bytes_display = f"{self.status.bytes_transferred/(1024**2):.2f} MB"
            else:
                bytes_display = f"{self.status.bytes_transferred/1024:.2f} KB"
            status_lines.append(f"[cyan]📦 Data Transferred:[/cyan] {bytes_display}")
        
        if self.status.files_transferred > 0:
            if self.status.total_files > 0:
                status_lines.append(f"[cyan]📄 Files:[/cyan] {self.status.files_transferred}/{self.status.total_files}")
            else:
                status_lines.append(f"[cyan]📄 Files:[/cyan] {self.status.files_transferred}")
        
        if hasattr(self.status, 'encryption_status'):
            if self.status.encryption_status == "encrypting":
                status_lines.append("[yellow]🔒 Encrypting backup...[/yellow]")
            elif self.status.encryption_status == "encrypted":
                status_lines.append("[green]🔒 Backup encrypted[/green]")
            elif self.status.encryption_status == "failed":
                status_lines.append("[red]🔒 Encryption failed[/red]")
        
        if self.status.errors:
            status_lines.append(f"[red]Errors: {len(self.status.errors)}[/red]")
            for error in self.status.errors[-2:]:  # Show last 2 errors
                status_lines.append(f"  [red]•[/red] {error[:55]}")
        if self.status.warnings:
            status_lines.append(f"[yellow]Warnings: {len(self.status.warnings)}[/yellow]")
            for warning in self.status.warnings[-2:]:  # Show last 2 warnings
                status_lines.append(f"  [yellow]•[/yellow] {warning[:55]}")
        if not status_lines:
            status_lines.append("[green]No errors or warnings[/green]")
        
        layout["status"].update(
            Panel("\n".join(status_lines), title="Status", border_style="magenta", box=box.ROUNDED)
        )
        
        # Footer with controls
        footer_content = """
[dim]Controls:[/dim] [bold]Q[/bold] = Quit/Cancel  [bold]P[/bold] = Pause  [bold]S[/bold] = Skip Current  [bold]H[/bold] = Help
"""
        layout["footer"].update(
            Panel(footer_content.strip(), border_style="dim", box=box.SIMPLE)
        )
        
        return layout
    
    def run_with_live_dashboard(self, operation: Callable, *args, **kwargs):
        """Run operation with live dashboard."""
        import sys
        import select
        
        # Check if we have a TTY for screen mode
        use_screen = sys.stdout.isatty() and sys.stdin.isatty()
        
        # Run operation in background
        operation_thread = threading.Thread(target=operation, args=args, kwargs=kwargs, daemon=True)
        operation_thread.start()
        
        # Update dashboard with keyboard handling
        try:
            # Start with initial dashboard
            # Use screen=True only if we have a TTY, otherwise use regular Live updates
            with Live(self.create_live_dashboard(), refresh_per_second=4, screen=use_screen) as live:
                while operation_thread.is_alive() and self.status.status not in ["cancelled", "completed", "error"]:
                    # Check for keyboard input (non-blocking)
                    if sys.stdin.isatty():
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            try:
                                import termios
                                import tty
                                old_settings = termios.tcgetattr(sys.stdin)
                                tty.setcbreak(sys.stdin.fileno())
                                key = sys.stdin.read(1)
                                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                                
                                if key.lower() == 'q':
                                    self.status.cancel()
                                    self.cancelled = True
                                    break
                                elif key.lower() == 'p':
                                    if self.status.status == "running":
                                        self.status.status = "paused"
                                    elif self.status.status == "paused":
                                        self.status.status = "running"
                                elif key.lower() == 's':
                                    # Skip current item
                                    self.status.skip_current = True
                                elif key.lower() == 'h':
                                    # Show help screen
                                    self._show_help_screen()
                            except (ImportError, OSError, AttributeError):
                                # Fallback if termios not available (Windows, etc.)
                                pass
                    
                    # Update dashboard with latest status
                    live.update(self.create_live_dashboard())
                    time.sleep(0.25)
                
                # Final update
                live.update(self.create_live_dashboard())
        except KeyboardInterrupt:
            self.status.cancel()
            self.cancelled = True
        
        # Wait for operation to complete
        operation_thread.join(timeout=2)
        
        return self.status.status == "completed"
    
    def select_containers(self, containers: List[Dict]) -> Set[str]:
        """Interactive container selection."""
        self.console.print("\n[bold]Select Containers to Backup:[/bold]\n")
        
        # Create selection table
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("ID", style="dim", width=12)
        table.add_column("Name", style="cyan", width=30)
        table.add_column("Status", width=12)
        table.add_column("Image", style="dim", width=30)
        
        for i, container in enumerate(containers, 1):
            status_color = "green" if container["status"] == "running" else "yellow"
            table.add_row(
                str(i),
                container["name"],
                f"[{status_color}]{container['status']}[/{status_color}]",
                container["image"][:30],
            )
        
        self.console.print(table)
        
        # Get selection
        self.console.print("\n[dim]Enter container numbers (comma-separated) or 'all' for all containers:[/dim]")
        selection = Prompt.ask("Selection", default="all")
        
        if selection.lower() == "all":
            return {c["name"] for c in containers}
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected = {containers[i]["name"] for i in indices if 0 <= i < len(containers)}
            return selected
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection, using all containers[/red]")
            return {c["name"] for c in containers}
    
    def select_backup_set(self) -> Optional[BackupSet]:
        """Select backup set from configuration."""
        if not self.config.backup_sets:
            return None
        
        self.console.print("\n[bold]Available Backup Sets:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Description", width=40)
        table.add_column("Containers", style="dim", width=30)
        
        sets_list = list(self.config.backup_sets.values())
        for i, backup_set in enumerate(sets_list, 1):
            containers_str = ", ".join(backup_set.containers[:3])
            if len(backup_set.containers) > 3:
                containers_str += f" (+{len(backup_set.containers) - 3} more)"
            table.add_row(
                str(i),
                backup_set.description or backup_set.name,
                containers_str,
            )
        
        self.console.print(table)
        
        self.console.print("\n[dim]Select backup set number, or press Enter to skip:[/dim]")
        selection = Prompt.ask("Selection", default="")
        
        if not selection:
            return None
        
        try:
            index = int(selection.strip()) - 1
            if 0 <= index < len(sets_list):
                return sets_list[index]
        except ValueError:
            pass
        
        return None
    
    def select_scope(self) -> Dict[str, bool]:
        """Select backup scope."""
        self.console.print("\n[bold]Select Backup Scope:[/bold]\n")
        
        scope = {
            "containers": Confirm.ask("Backup container configurations?", default=True),
            "volumes": Confirm.ask("Backup data volumes?", default=True),
            "networks": Confirm.ask("Backup network configurations?", default=True),
            "configs": Confirm.ask("Backup container configs/metadata?", default=True),
        }
        
        return scope
    
    def _show_help_screen(self):
        """Display help screen with keyboard shortcuts."""
        help_content = """
[bold cyan]bbackup - Keyboard Controls[/bold cyan]

[bold]Q[/bold] - Quit/Cancel backup
  Cancels the current backup operation and exits

[bold]P[/bold] - Pause/Resume backup
  Pauses or resumes the backup operation

[bold]S[/bold] - Skip current item
  Skips the current container/volume/network being backed up

[bold]H[/bold] - Help (this screen)
  Shows this help screen

[dim]Press any key to close help...[/dim]
"""
        from rich.panel import Panel
        self.console.print(Panel(help_content.strip(), title="Help", border_style="cyan", box=box.ROUNDED))
        # In the live dashboard, this would be shown in a modal/overlay
        # For now, it's printed to console
    
    def show_backup_status(self, results: Dict, errors: List[str]):
        """Display backup results."""
        self.console.print("\n[bold]Backup Results:[/bold]\n")
        
        # Success summary
        table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
        table.add_column("Type", style="cyan", width=15)
        table.add_column("Success", style="green", width=10)
        table.add_column("Failed", style="red", width=10)
        
        containers_success = sum(1 for v in results.get("containers", {}).values() if v == "success")
        containers_failed = sum(1 for v in results.get("containers", {}).values() if v == "failed")
        volumes_success = sum(1 for v in results.get("volumes", {}).values() if v == "success")
        volumes_failed = sum(1 for v in results.get("volumes", {}).values() if v == "failed")
        networks_success = sum(1 for v in results.get("networks", {}).values() if v == "success")
        networks_failed = sum(1 for v in results.get("networks", {}).values() if v == "failed")
        
        fs_success = sum(1 for v in results.get("filesystems", {}).values() if v == "success")
        fs_failed = sum(1 for v in results.get("filesystems", {}).values() if v == "failed")

        table.add_row("Containers", str(containers_success), str(containers_failed))
        table.add_row("Volumes", str(volumes_success), str(volumes_failed))
        table.add_row("Networks", str(networks_success), str(networks_failed))
        table.add_row("Filesystems", str(fs_success), str(fs_failed))
        
        self.console.print(table)
        
        # Errors
        if errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for error in errors:
                self.console.print(f"  [red]•[/red] {error}")
