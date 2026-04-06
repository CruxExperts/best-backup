#!/usr/bin/env python3
"""
bbman.py
Purpose: bbackup Management Wrapper. Provides setup, health, dependency,
         status, cleanup, diagnostics, update, and run subcommands with
         AI-agent-friendly JSON I/O via --output json, --input-json, and
         the `skills` subcommand for progressive capability discovery.
Created: 2025-01-01
Last Updated: 2026-03-04
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

# Gap 12: import __version__ instead of hardcoding "1.0.0"
from bbackup import __version__

from bbackup.cli_utils import (
    output_option,
    input_json_option,
    merge_json_input,
    render_output,
    json_error,
    flatten_health_tuples,
    EXIT_SUCCESS,
    EXIT_USER_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_SYSTEM_ERROR,
    EXIT_PARTIAL,
    EXIT_CANCELLED,
    BBACKUP_NO_INTERACTIVE_ENV,
)
from bbackup.skills import get_skill


SKILLS_DOC_PATH = Path(__file__).parent / "docs" / "cli-skills.md"
SKILLS_INDEX_PATH = Path(__file__).parent / "docs" / "cli-skills-index.json"

# Default repository URL: auto-detected from git remote, then placeholder.
# Set BBACKUP_REPO_URL env var or run `bbman repo-url --url URL` to override.
try:
    _git_result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=2,
        cwd=Path(__file__).parent,
    )
    if _git_result.returncode == 0:
        DEFAULT_REPO_URL = _git_result.stdout.strip().replace(".git", "")
    else:
        DEFAULT_REPO_URL = "https://github.com/YOUR_USERNAME/best-backup"
except Exception:
    DEFAULT_REPO_URL = "https://github.com/YOUR_USERNAME/best-backup"

sys.path.insert(0, str(Path(__file__).parent))

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="bbman")
@click.pass_context
def cli(ctx):
    """bbman - bbackup Management Wrapper.

    Comprehensive management tool for bbackup: first-run setup, version
    checking, health diagnostics, cleanup, and more.
    Set BBACKUP_OUTPUT=json to make all commands emit structured JSON.
    Set BBACKUP_NO_INTERACTIVE=1 for fully non-interactive execution.
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = console

    try:
        from bbackup.management.repo import get_repo_url
        ctx.obj["repo_url"] = get_repo_url()
    except Exception:
        ctx.obj["repo_url"] = DEFAULT_REPO_URL

    try:
        from bbackup.management.first_run import is_first_run
        if is_first_run():
            console.print("[yellow]First run detected. Run 'bbman setup' to configure.[/yellow]")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--no-interactive",
    is_flag=True,
    default=False,
    help="Skip the interactive wizard; return current config state. Set BBACKUP_NO_INTERACTIVE=1 globally.",
)
@output_option
@input_json_option
@click.pass_context
def setup(ctx, no_interactive, output, input_json):
    """Run interactive setup wizard for first-time configuration."""
    merge_json_input(ctx, input_json)
    no_interactive = no_interactive or os.environ.get(BBACKUP_NO_INTERACTIVE_ENV) == "1"

    if no_interactive:
        # Non-interactive: skip wizard, return config state
        result = {
            "completed": False,
            "skipped_wizard": True,
            "config_path": None,
            "errors": ["Interactive setup required; re-run without --no-interactive"],
        }
        render_output(result, output, "setup", success=False, errors=result["errors"])
        if output != "json":
            console.print("[yellow]Wizard skipped (--no-interactive). Run without flag to configure.[/yellow]")
        sys.exit(EXIT_USER_ERROR)

    try:
        from bbackup.management.setup_wizard import run_setup_wizard
        success = run_setup_wizard()
        result = {"completed": success, "skipped_wizard": False}
        render_output(result, output, "setup", success=success)
        sys.exit(EXIT_SUCCESS if success else EXIT_SYSTEM_ERROR)
    except Exception as e:
        render_output({}, output, "setup", success=False, errors=[str(e)])
        if output != "json":
            console.print(f"[red]Error running setup wizard: {e}[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def health(ctx, skills, output, input_json):
    """Run comprehensive health check (Docker, rsync, rclone, Python packages)."""
    if skills:
        _print_command_skills("bbman", "health")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.management.health import run_health_check, display_health_report

        results = run_health_check()

        # Gap 3: flatten tuple values for JSON consumers
        json_results = flatten_health_tuples(results)
        render_output(json_results, output, "health", success=bool(results.get("all_critical_ok")))

        if output != "json":
            display_health_report(results)

        sys.exit(EXIT_SUCCESS if results.get("all_critical_ok") else EXIT_SYSTEM_ERROR)
    except Exception as e:
        render_output({}, output, "health", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error running health check: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# check-deps
# ---------------------------------------------------------------------------

@cli.command("check-deps")
@click.option("--install", "-i", is_flag=True, help="Install missing packages")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def check_deps(ctx, install, skills, output, input_json):
    """Check and optionally install missing dependencies."""
    if skills:
        _print_command_skills("bbman", "check-deps")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.management.dependencies import check_and_install_dependencies, display_dependency_report

        results = check_and_install_dependencies(install_missing=install)

        # Gap 3: flatten tuple values in nested "system" dict
        json_results = dict(results)
        if "system" in json_results and isinstance(json_results["system"], dict):
            json_results["system"] = flatten_health_tuples(json_results["system"])
        if "python_packages" in json_results and isinstance(json_results["python_packages"], tuple):
            json_results["python_packages"] = flatten_health_tuples(
                {"python_packages": json_results["python_packages"]}
            )["python_packages"]

        all_ok = results.get("python_all_installed", False)
        render_output(json_results, output, "check-deps", success=all_ok)

        if output != "json":
            display_dependency_report(results)

        sys.exit(EXIT_SUCCESS if all_ok else EXIT_SYSTEM_ERROR)
    except Exception as e:
        render_output({}, output, "check-deps", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error checking dependencies: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# validate-config
# ---------------------------------------------------------------------------

@cli.command("validate-config")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def validate_config(ctx, skills, output, input_json):
    """Validate configuration file."""
    if skills:
        _print_command_skills("bbman", "validate-config")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.config import Config

        config = Config()

        if not config.config_path:
            result = {
                "valid": False,
                "config_path": None,
                "backup_sets": 0,
                "enabled_remotes": 0,
                "encryption": "disabled",
                "message": "No config file found, using defaults. Run 'bbman setup' to create one.",
            }
            render_output(result, output, "validate-config", success=True)
            if output != "json":
                console.print("[yellow]No config file found, using defaults[/yellow]")
                console.print("[dim]Run 'bbman setup' to create a config file[/dim]")
            sys.exit(EXIT_SUCCESS)

        result = {
            "valid": True,
            "config_path": str(config.config_path),
            "backup_sets": len(config.backup_sets),
            "enabled_remotes": len([r for r in config.remotes.values() if r.enabled]),
            "encryption": "enabled" if config.encryption.enabled else "disabled",
        }
        render_output(result, output, "validate-config", success=True)
        if output != "json":
            console.print(f"[green]Config file valid: {config.config_path}[/green]")
            console.print(f"[dim]Backup sets: {result['backup_sets']}[/dim]")
            console.print(f"[dim]Enabled remotes: {result['enabled_remotes']}[/dim]")
            console.print(f"[dim]Encryption: {result['encryption']}[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "validate-config", success=False, errors=[str(e)])
        if output != "json":
            console.print(f"[red]Config validation failed: {e}[/red]")
        sys.exit(EXIT_CONFIG_ERROR)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def status(ctx, skills, output, input_json):
    """Show backup status and history."""
    if skills:
        _print_command_skills("bbman", "status")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.config import Config

        config = Config()

        # Gap 4: in JSON mode bypass display_backup_status() and use raw data
        if output == "json":
            try:
                from bbackup.management.status import get_backup_statistics, list_local_backups
                stats = get_backup_statistics(config)
                history = list_local_backups(config)
                result = {
                    "total_backups": stats.get("total_backups", 0),
                    "total_size_bytes": stats.get("total_size", 0),
                    "encrypted_backups": stats.get("encrypted_backups", 0),
                    "latest_backup": stats.get("latest_backup"),
                    "history": history,
                }
            except AttributeError:
                # Fallback: module may not expose these functions yet
                result = {"message": "Status module does not expose raw data functions; run without --output json for full report."}
            render_output(result, output, "status")
        else:
            from bbackup.management.status import display_backup_status
            display_backup_status(config)

        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "status", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error checking status: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--staging-days", default=7, help="Keep staging files newer than N days")
@click.option("--log-days", default=30, help="Keep log files newer than N days")
@click.option("--no-backups", is_flag=True, help="Don't cleanup old backups")
@click.option("--no-temp", is_flag=True, help="Don't cleanup temporary files")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def cleanup(ctx, staging_days, log_days, no_backups, no_temp, yes, skills, output, input_json):
    """Cleanup old files and backups."""
    if skills:
        _print_command_skills("bbman", "cleanup")
    merge_json_input(ctx, input_json)

    # In JSON mode skip interactive confirmation automatically
    if output == "json" and not yes:
        yes = True

    try:
        from bbackup.management.cleanup import run_cleanup
        from bbackup.config import Config

        config = Config()
        results = run_cleanup(
            config=config,
            staging_days=staging_days,
            log_days=log_days,
            cleanup_backups=not no_backups,
            cleanup_temp=not no_temp,
            confirm=not yes,
        )

        # Gap 5: use .get("kept", 0) to guarantee stable shape
        result_data = {
            "staging_removed": results.get("staging_removed", 0),
            "logs_removed": results.get("logs_removed", 0),
            "backups_removed": results.get("backups_removed", 0),
            "backups_kept": results.get("kept", 0),
            "backups_freed_bytes": results.get("backups_freed_space", 0),
            "temp_removed": results.get("temp_removed", 0),
        }

        total_removed = (
            result_data["staging_removed"]
            + result_data["logs_removed"]
            + result_data["backups_removed"]
            + result_data["temp_removed"]
        )
        result_data["total_removed"] = total_removed

        render_output(result_data, output, "cleanup")
        if output != "json":
            console.print(f"\n[green]Cleanup complete: {total_removed} items removed[/green]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "cleanup", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error during cleanup: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--report-file",
    "-f",
    type=click.Path(),
    help="Save diagnostics report to this file path",
)
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def diagnostics(ctx, report_file, skills, output, input_json):
    """Run diagnostics and optionally save report to file."""
    if skills:
        _print_command_skills("bbman", "diagnostics")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.management.diagnostics import run_diagnostics, display_diagnostics_report, generate_diagnostics_report
        from bbackup.config import Config

        config = Config()
        diagnostics_data = run_diagnostics(config)

        result_data = dict(diagnostics_data)
        if report_file:
            output_path = Path(report_file)
            generate_diagnostics_report(diagnostics_data, output_path)
            result_data["report_saved_to"] = str(output_path)

        render_output(result_data, output, "diagnostics")
        if output != "json":
            display_diagnostics_report(diagnostics_data)
            if report_file:
                console.print(f"\n[green]Report saved to: {report_file}[/green]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "diagnostics", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error running diagnostics: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# check-updates
# ---------------------------------------------------------------------------

@cli.command("check-updates")
@click.option("--branch", default="main", help="Branch to check (default: main)")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def check_updates(ctx, branch, skills, output, input_json):
    """Check for updates (file-level comparison with checksums)."""
    if skills:
        _print_command_skills("bbman", "check-updates")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.management.version import check_for_updates

        repo_root = Path(__file__).parent
        repo_url = ctx.obj.get("repo_url", DEFAULT_REPO_URL)

        if output != "json":
            console.print(f"[cyan]Checking for updates from {repo_url} (branch: {branch})...[/cyan]")

        result = check_for_updates(repo_root, repo_url, branch)

        if result.get("error"):
            render_output(result, output, "check-updates", success=False, errors=[result["error"]])
            if output != "json":
                console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(EXIT_SYSTEM_ERROR)

        render_output(result, output, "check-updates", success=True)

        if output != "json":
            if result.get("has_updates"):
                console.print("[yellow]Updates available![/yellow]")
                console.print(f"[dim]Changed files: {len(result.get('changed', []))}[/dim]")
                console.print(f"[dim]New files: {len(result.get('new', []))}[/dim]")
                console.print(f"[dim]Removed files: {len(result.get('removed', []))}[/dim]")
                if result.get("changed"):
                    console.print("\n[bold]Changed files:[/bold]")
                    for f in result["changed"][:10]:
                        console.print(f"  [yellow]x {f}[/yellow]")
                    if len(result["changed"]) > 10:
                        console.print(f"  [dim]... and {len(result['changed']) - 10} more[/dim]")
                console.print("\n[cyan]Run 'bbman update' to update[/cyan]")
            else:
                console.print("[green]No updates available[/green]")
                console.print(f"[dim]Local files: {result.get('local_count', 0)}, Remote files: {result.get('remote_count', 0)}[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "check-updates", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error checking updates: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--branch", default="main", help="Branch to update from (default: main)")
@click.option("--method", type=click.Choice(["git", "download"]), default="git", help="Update method")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def update(ctx, branch, method, yes, skills, output, input_json):
    """Update application files."""
    if skills:
        _print_command_skills("bbman", "update")
    merge_json_input(ctx, input_json)

    # In JSON mode skip interactive confirmation automatically
    if output == "json" and not yes:
        yes = True

    try:
        from bbackup.management.updater import perform_update
        from bbackup.management.version import check_for_updates

        repo_root = Path(__file__).parent
        repo_url = ctx.obj.get("repo_url", DEFAULT_REPO_URL)

        if output != "json":
            console.print(f"[cyan]Checking for updates from {repo_url} (branch: {branch})...[/cyan]")

        update_info = check_for_updates(repo_root, repo_url, branch)

        if not update_info.get("has_updates"):
            render_output({"has_updates": False}, output, "update")
            if output != "json":
                console.print("[green]No updates available[/green]")
            sys.exit(EXIT_SUCCESS)

        if output != "json":
            console.print(f"[yellow]Updates available:[/yellow]")
            console.print(f"  [dim]Changed: {len(update_info.get('changed', []))} files[/dim]")
            console.print(f"  [dim]New: {len(update_info.get('new', []))} files[/dim]")
            console.print(f"  [dim]Removed: {len(update_info.get('removed', []))} files[/dim]")

        if not yes and output != "json":
            from rich.prompt import Confirm
            if not Confirm.ask("Proceed with update?", default=True):
                render_output({"cancelled": True}, output, "update", success=False, errors=["Update cancelled by user"])
                console.print("[dim]Update cancelled[/dim]")
                sys.exit(EXIT_CANCELLED)

        if output != "json":
            console.print(f"[cyan]Updating using {method} method...[/cyan]")

        result = perform_update(repo_root, repo_url, branch, method)

        render_output(result, output, "update", success=bool(result.get("success")))
        if output != "json":
            if result.get("success"):
                console.print(f"[green]Update completed successfully![/green]")
                console.print(f"[dim]Files updated: {result.get('files_updated', 0)}[/dim]")
                if result.get("backup_dir"):
                    console.print(f"[dim]Backup saved to: {result['backup_dir']}[/dim]")
            else:
                console.print(f"[red]Update failed: {result.get('message', 'Unknown error')}[/red]")
                sys.exit(EXIT_SYSTEM_ERROR)
        sys.exit(EXIT_SUCCESS if result.get("success") else EXIT_SYSTEM_ERROR)
    except Exception as e:
        render_output({}, output, "update", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error during update: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# repo-url
# ---------------------------------------------------------------------------

@cli.command("repo-url")
@click.option("--url", help="Set repository URL override")
@click.option(
    "--skills",
    is_flag=True,
    help="Show skills documentation for this command and exit.",
)
@output_option
@input_json_option
@click.pass_context
def repo_url(ctx, url, skills, output, input_json):
    """Show or set the repository URL override."""
    if skills:
        _print_command_skills("bbman", "repo-url")
    merge_json_input(ctx, input_json)

    try:
        from bbackup.management.repo import get_repo_url, set_repo_url, parse_repo_url

        if url:
            if set_repo_url(url):
                parsed = parse_repo_url(url)
                result = {"set": True, "url": url, "parsed": parsed}
                render_output(result, output, "repo-url")
                if output != "json":
                    console.print(f"[green]Repository URL set to: {url}[/green]")
                    console.print(f"[dim]Type: {parsed['type']}, Owner: {parsed['owner']}, Repo: {parsed['repo']}[/dim]")
            else:
                render_output({}, output, "repo-url", success=False, errors=["Failed to set repository URL"])
                if output != "json":
                    console.print("[red]Failed to set repository URL[/red]")
                sys.exit(EXIT_SYSTEM_ERROR)
        else:
            current_url = get_repo_url()
            parsed = parse_repo_url(current_url)
            result = {"url": current_url, "parsed": parsed}
            render_output(result, output, "repo-url")
            if output != "json":
                console.print(f"[cyan]Current repository URL: {current_url}[/cyan]")
                if parsed["type"] != "unknown":
                    console.print(f"[dim]Type: {parsed['type']}, Owner: {parsed['owner']}, Repo: {parsed['repo']}[/dim]")
                console.print("[dim]Override via: BBACKUP_REPO_URL env var or config file[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        render_output({}, output, "repo-url", success=False, errors=[str(e)])
        if output != "json":
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("command", nargs=-1)
@output_option
@click.pass_context
def run(ctx, command, output):
    """Launch main bbackup application.

    Pass any bbackup command and arguments after 'run'.
    Example: bbman run backup --containers my_container --no-interactive --output json
    """
    try:
        from bbackup.cli import cli as bbackup_cli

        # Gap 13: in JSON mode capture subprocess output and wrap in envelope
        if output == "json":
            proc = subprocess.run(
                ["bbackup"] + list(command),
                capture_output=True,
                text=True,
            )
            render_output(
                {"exit_code": proc.returncode, "output": proc.stdout},
                output,
                "run",
                success=(proc.returncode == 0),
                errors=[proc.stderr] if proc.stderr.strip() else [],
            )
            sys.exit(proc.returncode)

        original_argv = sys.argv[:]
        try:
            if "run" in sys.argv:
                run_idx = sys.argv.index("run")
                sys.argv = ["bbackup"] + sys.argv[run_idx + 1:]
            else:
                sys.argv = ["bbackup"] + list(command) if command else ["bbackup"]
            bbackup_cli()
        finally:
            sys.argv = original_argv
    except ImportError as e:
        render_output({}, output, "run", success=False, errors=[str(e)])
        if output != "json":
            console.print(f"[red]Error importing bbackup: {e}[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)
    except Exception as e:
        render_output({}, output, "run", success=False, errors=[str(e)])
        if output != "json":
            import traceback
            console.print(f"[red]Error running bbackup: {e}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(EXIT_SYSTEM_ERROR)


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------

@cli.command("skills")
@click.argument("skill_id", required=False)
@click.option(
    "--format",
    "format_",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output as JSON (default) or Markdown skills catalog.",
)
@output_option
def skills(skill_id, format_, output):
    """List available skills for AI agent discovery, or dump the Markdown skills catalog."""
    if format_ == "markdown":
        _print_skills_markdown()
        return

    result = get_skill("bbman", skill_id)
    if result is None:
        json_error(
            "skills",
            f"Unknown skill: {skill_id!r}. Run 'bbman skills' for valid ids.",
            EXIT_USER_ERROR,
            output,
        )

    if skill_id is None:
        sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    else:
        render_output(result, output, "skills")
        if output != "json":
            console.print(f"\n[bold cyan]{result['id']}[/bold cyan]: {result['summary']}")
            console.print(f"\nWorkflow: {' -> '.join(result.get('workflow', []))}")
            console.print("\nExamples:")
            for ex in result.get("examples", []):
                console.print(f"  [dim]{ex}[/dim]")


def _print_command_skills(cli_name: str, command_name: str) -> None:
    """
    Print the skills documentation section for a specific CLI command and exit.
    """
    if not SKILLS_DOC_PATH.exists() or not SKILLS_INDEX_PATH.exists():
        console.print("[red]Skills documentation has not been generated yet.[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)

    try:
        index = json.loads(SKILLS_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        console.print(f"[red]Failed to read skills index: {exc}[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)

    cmd_id = f"{cli_name}:{command_name}"
    meta = index.get(cmd_id)
    if not meta:
        console.print(f"[red]No skills entry found for command {cmd_id}.[/red]")
        sys.exit(EXIT_USER_ERROR)

    lines = SKILLS_DOC_PATH.read_text(encoding="utf-8").splitlines()
    start = max(int(meta.get("start", 1)) - 1, 0)
    end = min(int(meta.get("end", len(lines))), len(lines))
    section = "\n".join(lines[start:end]) + "\n"
    sys.stdout.write(section)
    sys.exit(EXIT_SUCCESS)


def _print_skills_markdown() -> None:
    """
    Print the full Markdown skills catalog to stdout and exit.
    """
    if not SKILLS_DOC_PATH.exists():
        console.print("[red]Skills documentation has not been generated yet.[/red]")
        sys.exit(EXIT_SYSTEM_ERROR)
    sys.stdout.write(SKILLS_DOC_PATH.read_text(encoding="utf-8"))
    sys.exit(EXIT_SUCCESS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
