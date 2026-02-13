#!/usr/bin/env python3
"""
SessionStart hook: Setup GitHub authentication from .env.local.

This hook runs at session start to:
1. Find .env.local (searching up directory tree for worktree support)
2. Load GITHUB_PAT from .env.local
3. Check if gh CLI can access the current repo
4. If not, automatically sync gh CLI auth with the found token

This ensures that gh CLI commands (like `gh pr create`) work even when:
- The token is in a parent directory's .env.local
- The gh CLI keyring has a different/expired token
"""

import sys
from pathlib import Path

# Add lib to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

try:
    from hook_utils import graceful_hook, get_project_dir, log_info, log_warning

    HAS_HOOK_UTILS = True
except ImportError:
    # Minimal fallback if hook_utils not available
    import os

    HAS_HOOK_UTILS = False

    def graceful_hook(blocking=False, name=None):
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

    def log_info(msg):
        print(f"[heo] {msg}", file=sys.stderr)

    def log_warning(msg):
        print(f"[heo] {msg}", file=sys.stderr)


try:
    from github_auth import find_env_local, validate_github_auth

    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False


@graceful_hook(blocking=False, name="github-auth-setup")
def main():
    if not HAS_AUTH:
        # Can't validate without the auth module
        sys.exit(0)

    project_dir = get_project_dir()

    # Skip if not a git repo (check for .git file or directory)
    git_path = project_dir / ".git"
    if not git_path.exists():
        sys.exit(0)

    # Import here to check if GitHub repo (get_repo_from_remote returns None if not)
    from github_auth import get_repo_from_remote

    repo_info = get_repo_from_remote(project_dir)
    if not repo_info:
        # Not a GitHub repo or no remote, skip silently
        sys.exit(0)

    # Validate and auto-fix auth
    result = validate_github_auth(project_dir, auto_fix=True)

    if not result.has_token:
        env_file = find_env_local(project_dir)
        if env_file:
            log_warning(f"REPO_ORIGIN_PAT not found in {env_file}")
        else:
            log_warning("No .env.local found (searched up to 10 parent dirs)")
        log_info("Add REPO_ORIGIN_PAT=<your-token> to .env.local")
        sys.exit(0)

    if result.repo_accessible:
        log_info(f"GitHub auth OK (from {result.token_source})")
    else:
        log_warning(f"GitHub auth issue: {result.error}")
        if result.fix_command:
            log_info(f"Fix: {result.fix_command}")

    sys.exit(0)


if __name__ == "__main__":
    main()
