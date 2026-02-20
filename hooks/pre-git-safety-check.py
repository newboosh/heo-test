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
     "--no-verify is not allowed. Git hooks must run.",
     "The --no-verify flag was blocked because it bypasses pre-commit hooks that enforce code quality. "
     "Remove --no-verify and let the hooks run. If a hook is failing, fix the underlying issue instead."),

    # Also catch --no-verify right after the subcommand
    (_GIT_PREFIX + r"(?:commit|push|merge|rebase|cherry-pick)\s+--no-verify",
     "--no-verify is not allowed. Git hooks must run.",
     "The --no-verify flag was blocked because it bypasses pre-commit hooks that enforce code quality. "
     "Remove --no-verify and let the hooks run. If a hook is failing, fix the underlying issue instead."),

    # Config overrides that bypass hooks or signing (this is in the flags, caught specially)
    (r"(?:^|[;&|`$(\s])(?:/[\w/.-]*)?git\s+-c\s+(?:core\.hooksPath|commit\.gpgSign|push\.gpgSign)\s*=",
     "Git config override (-c) for hooks/signing is not allowed.",
     "The -c config override for hooks/signing was blocked. Do not override core.hooksPath, "
     "commit.gpgSign, or push.gpgSign. These settings ensure code integrity."),

    # Direct push to main/master - also catch refspec syntax (HEAD:main, feature:main)
    (_GIT_PREFIX + r"push\s+(?:origin|upstream)\s+(?:[\w./-]+:)?(?:main|master)(?:\s|$)",
     "Direct push to main/master is not allowed. Create a feature branch and PR instead.",
     "Direct push to main/master was blocked. Use this workflow instead:\n"
     "1. Create a feature branch: git checkout -b feature/<name>\n"
     "2. Commit your changes on the feature branch\n"
     "3. Push the feature branch: git push -u origin feature/<name>\n"
     "4. Create a PR: gh pr create\n"
     "Or use /push which handles this workflow automatically."),

    # Force push to main/master - catch --force or -f in various positions
    (_GIT_PREFIX + r"push\s+(?:--force|-f)\s+\S+\s+(?:[\w./-]+:)?(?:main|master)(?:\s|$)",
     "Force push to main/master is not allowed. This would destroy history.",
     "Force push to main/master was blocked — this would rewrite shared history. "
     "If you need to update a feature branch, use --force-with-lease instead of --force. "
     "Never force-push to main/master."),

    (_GIT_PREFIX + r"push\s+\S+\s+(?:[\w./-]+:)?(?:main|master)\s+(?:--force|-f)",
     "Force push to main/master is not allowed. This would destroy history.",
     "Force push to main/master was blocked — this would rewrite shared history. "
     "If you need to update a feature branch, use --force-with-lease instead of --force. "
     "Never force-push to main/master."),

    # Destructive operations - with optional path and flags
    (_GIT_PREFIX + r"reset\s+--hard",
     "git reset --hard is destructive. Use git stash or git checkout <file> instead.",
     "git reset --hard was blocked because it permanently discards uncommitted changes. "
     "Safe alternatives:\n"
     "- git stash (saves changes, retrievable later)\n"
     "- git checkout <specific-file> (reverts one file)\n"
     "- git reset --soft HEAD~1 (undo commit, keep changes staged)"),

    (_GIT_PREFIX + r"clean\s+-\w*f",
     "git clean -f is destructive. Review untracked files manually.",
     "git clean -f was blocked because it permanently deletes untracked files. "
     "Safe alternatives:\n"
     "- git clean -n (dry run — shows what would be deleted)\n"
     "- Manually review and delete specific files\n"
     "- git stash --include-untracked (saves untracked files)"),

    (_GIT_PREFIX + r"checkout\s+--\s+\.",
     "git checkout -- . discards all changes. Use git stash instead.",
     "git checkout -- . was blocked because it discards ALL uncommitted changes in every file. "
     "Safe alternatives:\n"
     "- git stash (saves all changes, retrievable with git stash pop)\n"
     "- git checkout -- <specific-file> (reverts one file only)\n"
     "- git diff to review what would be lost first"),
]


def check_command(command: str):
    """
    Check if a command is allowed.

    Returns:
        (allowed, message, context) - allowed=False means block,
        message explains why (stderr), context provides model-visible guidance
    """
    for pattern, message, context in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, message, context

    return True, "", ""


@graceful_hook(blocking=True, name="git-safety-check")  # Fail secure - block on errors
def main():
    input_data = read_hook_input()
    result = HookResult()

    # Extract command from tool input
    command = input_data.get("tool_input", {}).get("command", "")

    if not command or "git" not in command:
        result.exit()

    # Check against blocked patterns
    allowed, message, context = check_command(command)

    if not allowed:
        cmd_display = command[:100] + "..." if len(command) > 100 else command
        print(f"[heo] Command: {cmd_display}", file=sys.stderr)
        result.block(message, command=command)
        if context:
            result.add_context(context)

    result.exit()


if __name__ == "__main__":
    main()
