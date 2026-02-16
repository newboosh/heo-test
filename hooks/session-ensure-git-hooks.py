#!/usr/bin/env python3
"""
SessionStart hook: Ensure project has git hooks configured.

Detects the project's hook tool (Husky, pre-commit, lefthook) and
warns if hooks are not installed.
"""

import sys
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_warning, log_info
    from git_hooks_manager import get_hook_status, detect_project_type
except ImportError:
    # Minimal fallback
    import os

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

    def get_hook_status(p):
        return {"tool": "none", "hooks_installed": False}

    def detect_project_type(p):
        return "unknown"

# Import safeguards separately - it may fail independently
try:
    from safeguards import is_heo_project, log_diagnostic
    SAFEGUARDS_AVAILABLE = True
except ImportError:
    SAFEGUARDS_AVAILABLE = False
    def is_heo_project(_p=None): return True, "fallback"
    def log_diagnostic(msg, **_): pass


@graceful_hook(blocking=False)
def main():
    project_dir = get_project_dir()

    # SAFEGUARD: Skip if not a heo-compatible project
    is_heo, reason = is_heo_project(project_dir)
    if not is_heo:
        log_diagnostic(f"Skipping git hooks check: {reason}")
        sys.exit(0)

    log_diagnostic("session-ensure-git-hooks started")

    # Skip if not a git repo
    if not (project_dir / ".git").exists():
        log_diagnostic("Not a git repo, skipping")
        sys.exit(0)

    status = get_hook_status(project_dir)

    if status["tool"] == "none":
        project_type = status.get("project_type", "unknown")

        log_warning("No git hooks configured for this project")

        if project_type == "python":
            log_info("Suggested: pre-commit")
            log_info("  pip install pre-commit")
            log_info("  pre-commit install")
        elif project_type == "node":
            log_info("Suggested: husky")
            log_info("  npm install --save-dev husky")
            log_info("  npx husky init")
        else:
            log_info("Suggested: pre-commit (language-agnostic)")
            log_info("  pip install pre-commit && pre-commit install")

    elif not status["hooks_installed"]:
        tool = status["tool"]
        log_warning(f"Git hooks not installed (config exists for {tool})")

        if tool == "pre-commit":
            log_info("Run: pre-commit install")
        elif tool == "husky":
            log_info("Run: npx husky install")
        elif tool == "lefthook":
            log_info("Run: lefthook install")

    # Exit successfully - this is informational only
    sys.exit(0)


if __name__ == "__main__":
    main()
