# PreToolUse Validation Hooks

Examples of hooks that validate and optionally block tool calls.

---

## Git Safety Hook

Blocks dangerous git operations like `--no-verify` and direct push to main.

### Configuration

Add to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/pre-git-safety-check.py\""
          }
        ],
        "description": "[frosty] Git safety: block --no-verify and direct push to main"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/pre-git-safety-check.py`:

```python
#!/usr/bin/env python3
"""
Git safety check for Claude Code PreToolUse hook.
Reads hook input from stdin, checks for dangerous git operations.
Exit code 2 = block the command (Claude Code convention)
"""

import json
import re
import sys

BLOCKED_PATTERNS = [
    # --no-verify bypasses git hooks
    (r"\bgit\s+.*--no-verify",
     "--no-verify is not allowed. Git hooks must run."),

    # Direct push to main/master
    (r"\bgit\s+push\s+(?:origin|upstream)\s+(?:main|master)(?:\s|$)",
     "Direct push to main/master is not allowed. Create a feature branch and PR."),

    # Force push to main/master
    (r"\bgit\s+push.*(?:--force|-f).*(?:main|master)",
     "Force push to main/master is not allowed. This would destroy history."),

    # Destructive operations
    (r"\bgit\s+reset\s+--hard",
     "git reset --hard is destructive. Use git stash instead."),
]

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Fail open if can't parse

    command = input_data.get("tool_input", {}).get("command", "")
    if not command or "git" not in command:
        sys.exit(0)

    for pattern, message in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"[frosty] BLOCKED: {message}", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
```

```bash
chmod +x .claude/hooks/pre-git-safety-check.py
```

**Note:** The frosty plugin automatically syncs this hook to projects on session start.
You don't need to manually add it if using the plugin.

---

## Dangerous Command Blocker

Blocks potentially destructive shell commands.

### Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' | { read cmd; if echo \"$cmd\" | grep -qE '(rm -rf /|mkfs|dd if=|:(){ :|:& };:|chmod -R 777 /)'; then echo '[Hook] BLOCKED: Dangerous command' >&2; exit 2; fi; }"
          }
        ],
        "description": "Block dangerous shell commands"
      }
    ]
  }
}
```

---

## SQL Write Blocker

Blocks SQL modification statements (for read-only database access).

### Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' | { read cmd; if echo \"$cmd\" | grep -iE '\\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\\b' > /dev/null; then echo '[Hook] BLOCKED: Write operations not allowed' >&2; exit 2; fi; }"
          }
        ],
        "description": "Block SQL write operations"
      }
    ]
  }
}
```

---

## Command Logging Hook

Logs all Bash commands for audit trail.

### Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"[\\(now | strftime(\"%Y-%m-%d %H:%M:%S\"))] \\(.tool_input.command)\"' >> \"$HOME/.claude/command-audit.log\""
          }
        ],
        "description": "Log all Bash commands"
      }
    ]
  }
}
```

---

## Testing PreToolUse Hooks

1. Add the hook configuration
2. Ask Claude to run a command that should be blocked
3. Verify the hook blocks with exit code 2
4. Check that allowed commands still work

Example test:
```
User: "Run git commit --no-verify -m 'test'"
Expected: Hook blocks with message about --no-verify
```
