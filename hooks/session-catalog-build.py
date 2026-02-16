#!/usr/bin/env python3
"""
SessionStart hook: Build catalog incrementally at session start.

Ensures AI agents have fresh file classification and dependency indexes
when starting a Claude Code session.
"""

import subprocess
import sys
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_info
except ImportError:
    import os

    def graceful_hook(blocking=False):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[catalog] Hook error: {e}", file=sys.stderr)
                    sys.exit(0)
            return wrapper
        return decorator

    def get_project_dir():
        return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))

    def log_info(msg):
        print(f"[catalog] {msg}", file=sys.stderr)

# Import safeguards separately
try:
    from safeguards import is_heo_project, log_diagnostic
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def is_heo_project(p=None): return True, "fallback"
    def log_diagnostic(msg, **_): pass


def has_catalog_config(project_dir: Path) -> bool:
    """Check if project has catalog configuration."""
    # Check new default location
    if (project_dir / ".claude" / "catalog" / "config.yaml").exists():
        return True
    # Check legacy location
    if (project_dir / "catalog.yaml").exists():
        return True
    return False


def run_catalog_build(project_dir: Path) -> bool:
    """Run catalog build --incremental."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.catalog.cli", "build", "--incremental"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            # Parse output for summary
            for line in result.stdout.splitlines():
                if "Classified" in line or "Analyzed" in line:
                    log_info(line.strip())
            return True
        elif result.returncode == 3:  # PARTIAL_SUCCESS
            log_info("Catalog built (some files skipped)")
            return True
        else:
            log_diagnostic(f"Catalog build failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        log_diagnostic("Catalog build timed out")
        return False
    except (OSError, subprocess.SubprocessError) as e:
        # OSError: command not found, permission denied, etc.
        # SubprocessError: other subprocess-related errors
        log_diagnostic(f"Catalog build error: {e}")
        return False


@graceful_hook(blocking=False)
def main():
    project_dir = get_project_dir()

    # SAFEGUARD: Skip if not a heo-compatible project
    is_heo, reason = is_heo_project(project_dir)
    if not is_heo:
        log_diagnostic(f"Skipping catalog build: {reason}")
        sys.exit(0)

    log_diagnostic("session-catalog-build started")

    # Skip if no catalog config
    if not has_catalog_config(project_dir):
        log_diagnostic("No catalog config found, skipping")
        sys.exit(0)

    # Run incremental build
    log_info("Building catalog (incremental)...")
    if run_catalog_build(project_dir):
        log_info("Catalog ready")

    sys.exit(0)


if __name__ == "__main__":
    main()
