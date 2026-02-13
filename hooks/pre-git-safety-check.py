#!/usr/bin/env python3
"""
Git safety check for Claude Code PreToolUse hook.

Reads hook input from stdin, checks for dangerous git operations,
and exits with code 2 to block if found.

Exit codes:
  0 = Allow the command
  2 = Block the command (Claude Code convention)
"""

import re
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from fallbacks import import_hook_utils
graceful_hook, read_hook_input, HookResult, _, _ = import_hook_utils()


# Dangerous patterns to block
# Note: Patterns are checked against the full command, not just git commands,
# to catch piped commands like `echo | git push --no-verify`
#
# Pattern components:
#   (?:^|[;&|`$(\s]) - match at start or after shell operators
#   (?:/[\w/.-]*)?git - git binary with optional path prefix
#   (?:\s+-\w+(?:\s+\S+)?)*\s+ - optional flags (with possible args) between git and subcommand
#   (?:[\w./-]+:)? - optional refspec prefix (HEAD:, feature:)
#
# Common git global flags that take arguments: -C <path>, -c <key>=<value>, --git-dir=<path>

# Helper pattern for git with optional path and global flags
_GIT_PREFIX = r"(?:^|[;&|`$(\s])(?:/[\w/.-]*)?git(?:\s+(?:-C\s+\S+|-c\s+\S+|--git-dir[=\s]\S+|-\w+))*\s+"

BLOCKED_PATTERNS = [
    # --no-verify bypasses git hooks
    # Match git with optional path, flags before subcommand, and --no-verify flag
    (_GIT_PREFIX + r"(?:commit|push|merge|rebase|cherry-pick)(?:\s+[^'\"]*?)?\s+--no-verify",
     "--no-verify is not allowed. Git hooks must run."),

    # Also catch --no-verify right after the subcommand
    (_GIT_PREFIX + r"(?:commit|push|merge|rebase|cherry-pick)\s+--no-verify",
     "--no-verify is not allowed. Git hooks must run."),

    # Config overrides that bypass hooks or signing (this is in the flags, caught specially)
    (r"(?:^|[;&|`$(\s])(?:/[\w/.-]*)?git\s+-c\s+(?:core\.hooksPath|commit\.gpgSign|push\.gpgSign)\s*=",
     "Git config override (-c) for hooks/signing is not allowed."),

    # Direct push to main/master - also catch refspec syntax (HEAD:main, feature:main)
    (_GIT_PREFIX + r"push\s+(?:origin|upstream)\s+(?:[\w./-]+:)?(?:main|master)(?:\s|$)",
     "Direct push to main/master is not allowed. Create a feature branch and PR instead."),

    # Force push to main/master - catch --force or -f in various positions
    (_GIT_PREFIX + r"push\s+(?:--force|-f)\s+\S+\s+(?:[\w./-]+:)?(?:main|master)(?:\s|$)",
     "Force push to main/master is not allowed. This would destroy history."),

    (_GIT_PREFIX + r"push\s+\S+\s+(?:[\w./-]+:)?(?:main|master)\s+(?:--force|-f)",
     "Force push to main/master is not allowed. This would destroy history."),

    # Destructive operations - with optional path and flags
    (_GIT_PREFIX + r"reset\s+--hard",
     "git reset --hard is destructive. Use git stash or git checkout <file> instead."),

    (_GIT_PREFIX + r"clean\s+-\w*f",
     "git clean -f is destructive. Review untracked files manually."),

    (_GIT_PREFIX + r"checkout\s+--\s+\.",
     "git checkout -- . discards all changes. Use git stash instead."),
]


def check_command(command: str):
    """
    Check if a command is allowed.

    Returns:
        (allowed, message) - allowed=False means block, message explains why
    """
    for pattern, message in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, message

    return True, ""


@graceful_hook(blocking=True, name="git-safety-check")  # Fail secure - block on errors
def main():
    input_data = read_hook_input()
    result = HookResult()

    # Extract command from tool input
    command = input_data.get("tool_input", {}).get("command", "")

    if not command or "git" not in command:
        result.exit()

    # Check against blocked patterns
    allowed, message = check_command(command)

    if not allowed:
        cmd_display = command[:100] + "..." if len(command) > 100 else command
        print(f"[frosty] Command: {cmd_display}", file=sys.stderr)
        result.block(message, command=command)

    result.exit()


if __name__ == "__main__":
    main()
