"""
Agentic sandbox test runner for bbackup.
Builds a Docker test image, runs pytest inside it, streams output live,
and on failure applies targeted auto-fixes then retries. Writes a final
local report to .localsetup/reports/ci-test-report.md regardless of outcome.

Usage:
    uv run python scripts/run_tests.py [--unit] [--integration] [--all]
                                       [--no-sandbox] [--max-retries N]

Default: --unit (excludes integration tests).
--no-sandbox: runs pytest directly on host without Docker (useful for CI).

Created: 2026-02-26
Last Updated: 2026-02-26
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
REPORT_DIR = REPO_ROOT / ".localsetup" / "reports"
REPORT_FILE = REPORT_DIR / "ci-test-report.md"
IMAGE_TAG = "bbackup:test"
MAX_RETRIES_DEFAULT = 3


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="bbackup agentic test runner")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--unit", action="store_true", default=True,
                            help="Run unit tests only (default)")
    mode_group.add_argument("--integration", action="store_true",
                            help="Run integration tests only")
    mode_group.add_argument("--all", action="store_true",
                            help="Run all tests (unit + integration)")
    parser.add_argument("--no-sandbox", action="store_true",
                        help="Run pytest directly on host (skip Docker build)")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES_DEFAULT,
                        help=f"Max debug loop iterations (default: {MAX_RETRIES_DEFAULT})")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Docker build and run
# ---------------------------------------------------------------------------


def build_image():
    """Build the test Docker image from Dockerfile.test."""
    print(f"[run_tests] Building Docker image {IMAGE_TAG}...")
    result = subprocess.run(
        ["docker", "build", "-f", "Dockerfile.test", "-t", IMAGE_TAG, "."],
        cwd=REPO_ROOT,
        capture_output=False,
    )
    if result.returncode != 0:
        print("[run_tests] Docker build failed. Cannot proceed.")
        sys.exit(1)
    print(f"[run_tests] Image {IMAGE_TAG} built successfully.")


def run_pytest_in_container(pytest_args: list, output_dir: Path) -> tuple[int, str]:
    """
    Run pytest inside a Docker container.

    Mounts:
      - /var/run/docker.sock for integration tests
      - output_dir as /app/output for coverage reports

    Returns (exit_code, combined_output_text).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "docker", "run", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", f"{output_dir}:/app/output",
        IMAGE_TAG,
    ] + pytest_args

    print(f"[run_tests] Running: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines = []
    for line in process.stdout:
        print(line, end="")
        lines.append(line)
    process.wait()

    return process.returncode, "".join(lines)


def run_pytest_local(pytest_args: list) -> tuple[int, str]:
    """Run pytest directly on the host (--no-sandbox mode)."""
    cmd = [sys.executable, "-m", "pytest"] + pytest_args
    print(f"[run_tests] Running (local): {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines = []
    for line in process.stdout:
        print(line, end="")
        lines.append(line)
    process.wait()

    return process.returncode, "".join(lines)


# ---------------------------------------------------------------------------
# Failure pattern detection and targeted fixes
# ---------------------------------------------------------------------------


def detect_failure_patterns(output: str) -> list[dict]:
    """Parse pytest output and return list of {pattern, description, fix_fn} dicts."""
    patterns = []

    # Pattern 1: hardcoded version "1.0.0" not in output
    if re.search(r"AssertionError.*1\.0\.0|1\.0\.0.*not in.*output", output):
        patterns.append({
            "pattern": "hardcoded_version",
            "description": "cli.py uses hardcoded version '1.0.0' instead of bbackup.__version__",
        })

    # Pattern 2: AttributeError on mock (wrong patch target)
    attr_matches = re.findall(r"AttributeError: .+?'(\w+)' object has no attribute '(\w+)'", output)
    for obj_type, attr in attr_matches:
        patterns.append({
            "pattern": "wrong_mock_attr",
            "description": f"Mock AttributeError: {obj_type} has no attribute {attr}",
        })

    # Pattern 3: missing __init__.py
    if re.search(r"FileNotFoundError.*__init__\.py|ModuleNotFoundError.*tests", output):
        patterns.append({
            "pattern": "missing_init",
            "description": "Missing __init__.py in tests/ or integration/",
        })

    # Pattern 4: TypeError on wrong call signature
    type_errs = re.findall(r"TypeError: \w+\(\) got an unexpected keyword argument '(\w+)'", output)
    for arg in type_errs:
        patterns.append({
            "pattern": "wrong_call_signature",
            "description": f"Unexpected keyword argument: {arg}",
        })

    # Pattern 5: unrecoverable errors
    if re.search(r"ImportError|ModuleNotFoundError", output) and "tests" not in output:
        patterns.append({"pattern": "import_error", "description": "ImportError: package not installed"})

    if "SyntaxError" in output:
        patterns.append({"pattern": "syntax_error", "description": "SyntaxError introduced by a previous fix"})

    if re.search(r"docker.errors.DockerException|Cannot connect to the Docker daemon", output):
        patterns.append({"pattern": "docker_unavailable", "description": "Docker daemon not reachable"})

    return patterns


def apply_fix_hardcoded_version():
    """Patch cli.py to use bbackup.__version__ instead of hardcoded '1.0.0'."""
    cli_file = REPO_ROOT / "bbackup" / "cli.py"
    text = cli_file.read_text()
    old = '@click.version_option(version="1.0.0")'
    new = '@click.version_option(version=__import__("bbackup").__version__)'
    if old in text:
        cli_file.write_text(text.replace(old, new))
        print("[run_tests][fix] Patched cli.py: replaced hardcoded version with bbackup.__version__")
        return True
    return False


def apply_fixes(patterns: list[dict]) -> list[str]:
    """Apply auto-fixes for known failure patterns. Returns list of fix descriptions applied."""
    applied = []
    unrecoverable = {"import_error", "syntax_error", "docker_unavailable"}

    for p in patterns:
        if p["pattern"] in unrecoverable:
            print(f"[run_tests] Unrecoverable failure: {p['description']}. Aborting debug loop.")
            return None  # Signal unrecoverable

        if p["pattern"] == "hardcoded_version":
            if apply_fix_hardcoded_version():
                applied.append(p["description"])

        elif p["pattern"] == "missing_init":
            init_file = REPO_ROOT / "tests" / "integration" / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                applied.append("Created missing tests/integration/__init__.py")

    return applied


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def load_coverage_json(output_dir: Path) -> dict:
    """Load coverage.json if available."""
    cov_file = output_dir / "coverage.json"
    if cov_file.exists():
        try:
            return json.loads(cov_file.read_text())
        except Exception:
            pass
    return {}


def build_coverage_table(coverage_data: dict) -> str:
    """Format coverage data as markdown table."""
    if not coverage_data or "files" not in coverage_data:
        return "_Coverage data not available_\n"

    lines = ["| Module | Stmts | Missed | Coverage |", "|--------|-------|--------|----------|"]
    for filepath, data in sorted(coverage_data["files"].items()):
        if "bbackup" not in filepath:
            continue
        module = filepath.replace(str(REPO_ROOT) + "/", "")
        stmts = data.get("summary", {}).get("num_statements", 0)
        missed = data.get("summary", {}).get("missing_lines", 0)
        pct = data.get("summary", {}).get("percent_covered", 0)
        lines.append(f"| `{module}` | {stmts} | {missed} | {pct:.1f}% |")
    return "\n".join(lines) + "\n"


def write_report(
    exit_code: int,
    output: str,
    fixes_applied: list[str],
    attempt_count: int,
    coverage_data: dict,
):
    """Write ci-test-report.md to ignored local report state."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    python_version = sys.version.split()[0]
    status_icon = "PASSED" if exit_code == 0 else "FAILED"

    report_lines = [
        "# bbackup CI Test Report",
        "",
        f"**Status:** {status_icon}  ",
        f"**Timestamp:** {now}  ",
        f"**Python:** {python_version}  ",
        f"**Attempt count:** {attempt_count}  ",
        "",
    ]

    if fixes_applied:
        report_lines += [
            "## Auto-fixes applied",
            "",
        ]
        for fix in fixes_applied:
            report_lines.append(f"- {fix}")
        report_lines.append("")

    report_lines += [
        "## Coverage summary",
        "",
        build_coverage_table(coverage_data),
        "",
        "## Pytest output",
        "",
        "```",
        output[-8000:] if len(output) > 8000 else output,
        "```",
        "",
    ]

    REPORT_FILE.write_text("\n".join(report_lines))
    print(f"[run_tests] Report written to: {REPORT_FILE}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    # Determine pytest args based on mode
    if args.all:
        pytest_args = [
            "tests/",
            "--cov=bbackup",
            "--cov-report=json:output/coverage.json",
            "--cov-report=term-missing",
            "-v", "--tb=short",
        ]
    elif args.integration:
        pytest_args = [
            "tests/integration/",
            "-m", "integration",
            "-v", "--tb=short",
        ]
    else:
        pytest_args = [
            "tests/",
            "-m", "not integration",
            "--cov=bbackup",
            "--cov-report=json:output/coverage.json",
            "--cov-report=term-missing",
            "--tb=short", "-q",
        ]

    # Build image if using sandbox
    if not args.no_sandbox:
        build_image()

    output_dir = REPORT_DIR / "output"
    all_fixes = []
    attempt = 0
    exit_code = 1
    output = ""

    while attempt <= args.max_retries:
        attempt += 1
        print(f"\n[run_tests] === Attempt {attempt} / {args.max_retries + 1} ===\n")

        if args.no_sandbox:
            exit_code, output = run_pytest_local(pytest_args)
        else:
            exit_code, output = run_pytest_in_container(pytest_args, output_dir)

        if exit_code == 0:
            print("[run_tests] All tests passed.")
            break

        if attempt > args.max_retries:
            print("[run_tests] Max retries reached. Giving up.")
            break

        # Analyze failures and attempt fixes
        patterns = detect_failure_patterns(output)
        if not patterns:
            print("[run_tests] No known failure patterns found. Cannot auto-fix.")
            break

        fixes = apply_fixes(patterns)
        if fixes is None:
            print("[run_tests] Unrecoverable error encountered. Stopping.")
            break
        if not fixes:
            print("[run_tests] No fixes could be applied. Stopping.")
            break

        all_fixes.extend(fixes)
        print(f"[run_tests] Applied {len(fixes)} fix(es). Retrying...")

    # Load coverage report
    coverage_data = load_coverage_json(output_dir)

    # Write final report
    write_report(
        exit_code=exit_code,
        output=output,
        fixes_applied=all_fixes,
        attempt_count=attempt,
        coverage_data=coverage_data,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
