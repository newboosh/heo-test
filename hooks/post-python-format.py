#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format Python files after edits.

Uses project's virtual environment to run ruff, ensuring the correct
version and configuration is used.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Import utilities
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from fallbacks import import_hook_utils, import_venv_runner
graceful_hook, read_hook_input, _, write_hook_output, get_project_dir = import_hook_utils()
find_venv, find_package_manager, get_venv_tool_path = import_venv_runner()

try:
    from safeguards import (
        guard_hook_execution,
        safe_subprocess_run,
        is_heo_project,
        log_diagnostic,
    )
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    # Fail-closed: if safeguards are unavailable, block hook execution
    # to prevent macOS permission dialog floods
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return False
    def safe_subprocess_run(cmd, **kw):
        return False, "", "blocked: safeguards unavailable"
    def is_heo_project(_p=None): return False, "safeguards unavailable"
    def log_diagnostic(msg, **_): pass


def run_ruff(file_path: Path, project_dir: Path) -> bool:
    """
    Run ruff format on a file using the project's environment.

    Returns True if formatting succeeded, False otherwise.
    """
    def _run_formatter(cmd, cwd=None, tool_name="ruff") -> bool:
        """Execute formatter and return success status using safeguards."""
        try:
            success, stdout, stderr = safe_subprocess_run(
                cmd,
                cwd=str(cwd) if cwd else None,
                timeout=30,
                tool_name=tool_name,
            )

            if stderr and "blocked" in stderr.lower():
                log_diagnostic(f"Formatter blocked: {stderr}")
                return False

            if not success and os.environ.get("HEO_DEBUG"):
                if stderr:
                    print(f"[heo] ruff warning: {stderr[:100]}", file=sys.stderr)

            return success
        except Exception as e:
            if os.environ.get("HEO_DEBUG"):
                print(f"[heo] ruff error: {e}", file=sys.stderr)
            log_diagnostic(f"Formatter error: {e}")
            return False

    # Try package manager first
    pkg_manager = find_package_manager(project_dir)
    if pkg_manager:
        cmd = pkg_manager + ["ruff", "format", str(file_path)]
        return _run_formatter(cmd, cwd=project_dir, tool_name=pkg_manager[0])

    # Try venv
    venv_path = find_venv(project_dir)
    if venv_path:
        ruff_path = get_venv_tool_path(venv_path, "ruff")
        if ruff_path:
            return _run_formatter([str(ruff_path), "format", str(file_path)], tool_name="ruff")

    # Fallback to global ruff (check with shutil.which first - no subprocess)
    global_ruff = shutil.which("ruff")
    if global_ruff:
        return _run_formatter([global_ruff, "format", str(file_path)], tool_name="ruff")

    # No ruff found
    if os.environ.get("HEO_DEBUG"):
        print("[heo] ruff not found", file=sys.stderr)
    log_diagnostic("ruff not found anywhere")
    return False


# Pattern to match actual print() function calls, not pprint, blueprint, etc.
PRINT_PATTERN = re.compile(r'\bprint\s*\(')


def check_print_statements(file_path: Path) -> None:
    """Warn about print() statements in the file (runs after formatting)."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        prints_found = []
        for i, line in enumerate(lines, 1):
            # Skip lines marked as intentional debug
            if '# debug ok' in line.lower() or '# noqa' in line.lower():
                continue
            # Skip comments
            stripped = line.lstrip()
            if stripped.startswith('#'):
                continue
            # Use regex to match actual print() calls (not pprint, blueprint, etc.)
            if PRINT_PATTERN.search(line):
                # Additional heuristic: skip if print is in a string literal
                # Count quotes before the match - if odd, it's likely in a string
                before_print = line.split('print')[0] if 'print' in line else ''
                single_quotes = before_print.count("'") - before_print.count("\\'")
                double_quotes = before_print.count('"') - before_print.count('\\"')
                if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                    prints_found.append(f"  {i}: {line.rstrip()[:60]}")

        if prints_found:
            print(f"[heo] WARNING: print() found in {file_path.name}", file=sys.stderr)
            for p in prints_found[:3]:  # Show max 3
                print(p, file=sys.stderr)
            if len(prints_found) > 3:
                print(f"  ... and {len(prints_found) - 3} more", file=sys.stderr)
            print("[heo] Remove print() before committing", file=sys.stderr)
    except (IOError, UnicodeDecodeError):
        pass  # Silently skip files we can't read


@graceful_hook(blocking=False)  # Never block on format errors
def main():
    input_data = read_hook_input()

    # Extract file path
    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        write_hook_output(input_data)
        sys.exit(0)

    file_path = Path(file_path)
    if not file_path.exists():
        write_hook_output(input_data)
        sys.exit(0)

    # SAFEGUARD: Check if this is a heo-compatible project
    project_dir = get_project_dir()
    is_heo, reason = is_heo_project(project_dir)
    if not is_heo:
        log_diagnostic(f"Skipping Python format: {reason}")
        write_hook_output(input_data)
        sys.exit(0)

    # SAFEGUARD: Check subprocess limits
    if not guard_hook_execution():
        log_diagnostic("Guard blocked hook execution")
        write_hook_output(input_data)
        sys.exit(0)

    log_diagnostic(f"Formatting {file_path.name}")
    format_success = run_ruff(file_path, project_dir)

    # Ensure filesystem sync before reading (prevents stale reads after formatting)
    if format_success:
        try:
            # Touch file to ensure metadata is synced
            os.sync()
        except (OSError, AttributeError):
            pass  # os.sync() may not exist on all platforms

    # Check for print statements (after formatting, so we check final state)
    check_print_statements(file_path)

    # Pass through the input (PostToolUse hooks should echo input)
    write_hook_output(input_data)
    sys.exit(0)


if __name__ == "__main__":
    main()
