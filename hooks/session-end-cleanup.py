#!/usr/bin/env python3
"""
SessionEnd hook: Clean up session-specific state.

Runs when a Claude Code session ends. Handles:
1. Cleaning up .claude/session-config.json (session guard state)
2. Writing a session-end marker for next-session awareness
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_info
except ImportError:
    def graceful_hook(_blocking=False, _name=None):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except SystemExit:
                    raise
                except (OSError, IOError, ValueError, RuntimeError) as e:
                    print(f"[heo] Hook error: {e}", file=sys.stderr)
                    sys.exit(0)
            return wrapper
        return decorator

    def get_project_dir():
        return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))

    def log_info(msg):
        print(f"[heo] {msg}", file=sys.stderr)

try:
    from safeguards import is_heo_project, log_diagnostic
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def is_heo_project(_p=None): return True, "fallback"
    def log_diagnostic(msg, **_): pass


@graceful_hook(blocking=False, name="session-end-cleanup")
def main():
    project_dir = get_project_dir()

    is_heo, reason = is_heo_project(project_dir)
    if not is_heo:
        log_diagnostic(f"Skipping session-end cleanup: {reason}")
        sys.exit(0)

    # 1. Clean up session guard state
    session_config = project_dir / ".claude" / "session-config.json"
    if session_config.exists():
        try:
            session_config.unlink()
            log_diagnostic("Cleaned up session-config.json")
        except OSError:
            pass

    # 2. Write session-end marker for next-session awareness
    # This lets the next session know when the last session ended
    # and whether learning extraction happened
    claude_dir = project_dir / ".claude"
    if claude_dir.is_dir():
        marker = claude_dir / "last-session.json"
        try:
            marker_data = {
                "ended_at": datetime.now().isoformat(),
                "branch": _get_current_branch(project_dir),
            }
            marker.write_text(json.dumps(marker_data, indent=2) + "\n")
        except (OSError, IOError):
            pass

    sys.exit(0)


def _get_current_branch(project_dir: Path) -> str:
    """Get current git branch name, or 'unknown'."""
    git_bin = shutil.which("git")
    if not git_bin:
        return "unknown"
    try:
        result = subprocess.run(  # noqa: S603 — args are hardcoded
            [git_bin, "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
            cwd=str(project_dir),
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        return "unknown"


if __name__ == "__main__":
    main()
