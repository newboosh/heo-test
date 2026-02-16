#!/usr/bin/env python3
"""
SessionStart hook: Validate project has required tools installed.

Checks that tools configured in the project are actually available in
the virtual environment at compatible versions.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_warning, log_info
    from tool_requirements import get_project_tool_requirements
    from venv_runner import find_venv, find_package_manager, get_venv_tool_path
except ImportError:
    # Minimal fallback
    def graceful_hook(blocking=False):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[heo] Hook error: {e}", file=sys.stderr)
                    sys.exit(0)
            return wrapper
        return decorator

    def get_project_dir():
        return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))

    def log_warning(msg):
        print(f"[heo] {msg}", file=sys.stderr)

    def log_info(msg):
        print(f"[heo] {msg}", file=sys.stderr)

    def get_project_tool_requirements(p):
        return {}

    def find_venv(p):
        for n in [".venv", "venv"]:
            v = p / n
            if (v / "bin" / "python").exists():
                return v
        return None

    def find_package_manager(p):
        return None

    def get_venv_tool_path(v, t):
        p = v / "bin" / t
        return p if p.exists() else None

# Import safeguards separately - it may fail independently
try:
    from safeguards import (
        guard_hook_execution,
        safe_subprocess_run,
        is_heo_project,
        log_diagnostic,
    )
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def guard_hook_execution(): return True
    def safe_subprocess_run(cmd, **kw):
        # Accept cwd from kwargs and pass to subprocess.run
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=kw.get('timeout', 5),
            cwd=kw.get('cwd'),
        )
        return r.returncode == 0, r.stdout, r.stderr
    def is_heo_project(p=None): return True, "fallback"
    def log_diagnostic(msg, **_): pass


def get_installed_version(tool: str, project_dir: Path) -> Optional[str]:
    """Get the installed version of a tool."""
    venv = find_venv(project_dir)

    # Try venv first
    if venv:
        tool_path = get_venv_tool_path(venv, tool)
        if tool_path:
            try:
                success, stdout, stderr = safe_subprocess_run(
                    [str(tool_path), "--version"],
                    timeout=5,
                    tool_name=tool,
                )
                output = (stdout or "") + (stderr or "")
                match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
                if match:
                    return match.group(1)
            except Exception:
                pass

    # Try package manager (limit spawning - skip if safeguards block)
    pkg_manager = find_package_manager(project_dir)
    if pkg_manager:
        try:
            success, stdout, stderr = safe_subprocess_run(
                pkg_manager + [tool, "--version"],
                timeout=10,
                cwd=str(project_dir),
                tool_name=pkg_manager[0] if pkg_manager else "pkg-manager",
            )
            output = (stdout or "") + (stderr or "")
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
            if match:
                return match.group(1)
        except Exception:
            pass

    # Try global - use shutil.which first (no subprocess)
    global_tool = shutil.which(tool)
    if global_tool:
        try:
            success, stdout, stderr = safe_subprocess_run(
                [global_tool, "--version"],
                timeout=5,
                tool_name=tool,
            )
            output = (stdout or "") + (stderr or "")
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
            if match:
                return f"{match.group(1)} (global)"
        except Exception:
            pass

    return None


def version_compatible(required: Optional[str], installed: Optional[str]) -> bool:
    """Check if installed version is compatible with required."""
    if not required or not installed:
        return True  # No requirement or can't check

    # Strip "(global)" suffix
    installed = installed.replace(" (global)", "")

    try:
        req_parts = [int(x) for x in required.split(".")[:2]]
        inst_parts = [int(x) for x in installed.split(".")[:2]]

        # Major version must match, minor must be >= required
        if req_parts[0] != inst_parts[0]:
            return False
        if len(req_parts) > 1 and len(inst_parts) > 1:
            return inst_parts[1] >= req_parts[1]
        return True
    except (ValueError, IndexError):
        return True  # Can't parse, assume OK


@graceful_hook(blocking=False)  # Never block on validation errors
def main():
    # SAFEGUARD: Check if this is a heo-compatible project
    project_dir = get_project_dir()

    is_heo, reason = is_heo_project(project_dir)
    if not is_heo:
        log_diagnostic(f"Skipping tool validation: {reason}")
        sys.exit(0)

    if not guard_hook_execution():
        sys.exit(0)

    log_diagnostic("session-validate-tools started")

    # Get required tools
    requirements = get_project_tool_requirements(project_dir)
    if not requirements:
        log_diagnostic("No tool requirements found")
        sys.exit(0)

    # Only check tools that are configured (have config files)
    configured_tools = {
        name: info for name, info in requirements.items()
        if info.get("configured")
    }

    if not configured_tools:
        sys.exit(0)

    # Check each tool
    missing = []
    wrong_version = []
    using_global = []

    for tool, info in configured_tools.items():
        required_version = info.get("version")
        installed = get_installed_version(tool, project_dir)

        if not installed:
            missing.append((tool, required_version))
        elif "(global)" in str(installed):
            using_global.append((tool, installed.replace(" (global)", ""), required_version))
        elif required_version and not version_compatible(required_version, installed):
            wrong_version.append((tool, required_version, installed))

    # Report issues
    if missing:
        print("[heo] Missing tools in project venv:", file=sys.stderr)
        for tool, version in missing:
            ver_str = f" (need {version})" if version else ""
            print(f"  - {tool}{ver_str}", file=sys.stderr)

    if wrong_version:
        print("[heo] Version mismatches:", file=sys.stderr)
        for tool, required, installed in wrong_version:
            print(f"  - {tool}: need {required}, have {installed}", file=sys.stderr)

    if using_global:
        print("[heo] Using global (not venv) tools:", file=sys.stderr)
        for tool, version, required in using_global:
            req_str = f" (project needs {required})" if required else ""
            print(f"  - {tool} {version}{req_str}", file=sys.stderr)

    if missing or wrong_version:
        venv = find_venv(project_dir)
        if venv:
            print(f"\n[heo] To install missing tools:", file=sys.stderr)
            print(f"  source {venv}/bin/activate && pip install -r requirements-dev.txt", file=sys.stderr)
        else:
            print(f"\n[heo] No venv found. Create one:", file=sys.stderr)
            print(f"  python -m venv .venv && source .venv/bin/activate", file=sys.stderr)

    # Always exit 0 - this is informational, not blocking
    sys.exit(0)


if __name__ == "__main__":
    main()
