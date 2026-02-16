# Claude Code Hooks System

## Hook Types

Claude Code supports three hook types that execute at different points:

| Hook Type | When It Runs | Use Case |
|-----------|--------------|----------|
| **PreToolUse** | Before tool execution | Validation, parameter modification, warnings |
| **PostToolUse** | After tool execution | Auto-format, checks, logging |
| **Stop** | When session ends | Final verification, cleanup |

## Configuration

Hooks are configured in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "bash /path/to/pre-bash-hook.sh"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit",
        "command": "bash /path/to/post-edit-hook.sh"
      }
    ],
    "Stop": [
      {
        "command": "bash /path/to/cleanup-hook.sh"
      }
    ]
  }
}
```

## Useful Hook Examples

### PreToolUse Hooks

#### tmux Reminder for Long Commands
Suggests using tmux for commands that might exceed the 2-minute timeout:

```bash
#!/bin/bash
# pre-bash-tmux-reminder.sh
COMMAND="$1"

# Check for long-running commands
if echo "$COMMAND" | grep -qE "(pip install|npm install|pytest|make ci|flask db)"; then
    echo "TIP: Consider running this in tmux for long operations:"
    echo "  tmux new-session -d -s build '$COMMAND'"
    echo "  tmux attach -t build  # to watch progress"
fi
```

**Why tmux?**
- Bash commands have a 2-minute default timeout (max 10 minutes)
- tmux keeps processes running even if terminal disconnects
- You can detach and reattach to check progress
- Useful for: `pip install`, `pytest`, `make ci`, database migrations

#### Prevent Dangerous Git Operations
```python
#!/usr/bin/env python3
# pre-git-safety-check.py - reads hook input from stdin
import json
import re
import sys

BLOCKED_PATTERNS = [
    (r"\bgit\s+.*--no-verify", "--no-verify is not allowed. Git hooks must run."),
    (r"\bgit\s+push\s+(?:origin|upstream)\s+(?:main|master)(?:\s|$)",
     "Direct push to main/master is not allowed. Create a feature branch and PR."),
    (r"\bgit\s+reset\s+--hard", "git reset --hard is destructive."),
]

input_data = json.load(sys.stdin)
command = input_data.get("tool_input", {}).get("command", "")

for pattern, message in BLOCKED_PATTERNS:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"BLOCKED: {message}", file=sys.stderr)
        sys.exit(2)  # Exit code 2 = block in Claude Code

sys.exit(0)
```

### PostToolUse Hooks

#### Python Formatting After Edit
```bash
#!/bin/bash
# post-edit-format.sh
FILE="$1"

# Only format Python files
if [[ "$FILE" == *.py ]]; then
    ruff format "$FILE" 2>/dev/null
    ruff check --fix "$FILE" 2>/dev/null
fi
```

#### Type Check After Python Edit
```bash
#!/bin/bash
# post-edit-typecheck.sh
FILE="$1"

if [[ "$FILE" == *.py ]]; then
    mypy "$FILE" --ignore-missing-imports 2>&1 | head -20
fi
```

#### Log PR Creation
```bash
#!/bin/bash
# post-pr-log.sh
RESULT="$1"

if echo "$RESULT" | grep -q "github.com.*pull"; then
    PR_URL=$(echo "$RESULT" | grep -o "https://github.com[^ ]*")
    echo "PR Created: $PR_URL"
    echo "$(date): $PR_URL" >> ~/.claude/pr-log.txt
fi
```

### Stop Hooks

#### Final Audit
```bash
#!/bin/bash
# stop-audit.sh

# Check for debug statements in modified files
MODIFIED=$(git diff --name-only HEAD~1 2>/dev/null | grep "\.py$")
for file in $MODIFIED; do
    if grep -n "print(" "$file" 2>/dev/null | grep -v "# debug ok"; then
        echo "WARNING: print() found in $file"
    fi
    if grep -n "breakpoint()" "$file" 2>/dev/null; then
        echo "WARNING: breakpoint() found in $file"
    fi
done
```

## Using tmux with Claude Code

### Basic tmux Commands

```bash
# Start new session for long command
tmux new-session -d -s mysession "make ci"

# List sessions
tmux list-sessions

# Attach to watch progress
tmux attach -t mysession

# Detach (inside tmux): Ctrl+B, then D

# Kill session when done
tmux kill-session -t mysession
```

### When to Use tmux

| Command Type | Use tmux? | Reason |
|--------------|-----------|--------|
| `pip install -r requirements.txt` | Yes | Can take several minutes |
| `pytest` (full suite) | Yes | May exceed timeout |
| `make ci` | Yes | Runs multiple long checks |
| `flask db upgrade` | Maybe | Usually fast, but migrations can be slow |
| `git status` | No | Always fast |
| `ruff check .` | No | Usually fast |

### Alternative: run_in_background

Claude Code's Bash tool has a `run_in_background` parameter:

```python
# This runs in background, returns task_id
Bash(command="make ci", run_in_background=True)

# Check later with TaskOutput
TaskOutput(task_id="...", block=False)
```

## Hook Best Practices

1. **Keep hooks fast** - They run on every tool use
2. **Exit 0 for success** - Non-zero exits can block operations
3. **Use matchers wisely** - Only run hooks for relevant tools
4. **Log sparingly** - Too much output is distracting
5. **Test hooks manually first** - Before adding to config

## Project-Specific Hooks

For this project, hooks are auto-synced by the heo plugin on session start.
The plugin copies hook scripts to `.claude/hooks/` and merges hook config into
`.claude/settings.json`.

Example of synced hooks:

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
        "description": "[heo] Git safety: block --no-verify and direct push to main"
      }
    ]
  }
}
```

Hooks with `[heo]` prefix are managed by the plugin and will be updated automatically.
