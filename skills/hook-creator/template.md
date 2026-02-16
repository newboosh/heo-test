# Hook Template

## Configuration Template

Add to `.claude/settings.local.json` (project) or `~/.claude/settings.json` (user):

```json
{
  "hooks": {
    "HOOK_EVENT": [
      {
        "matcher": "TOOL_PATTERN",
        "hooks": [
          {
            "type": "command",
            "command": "INLINE_COMMAND_OR_SCRIPT_PATH"
          }
        ],
        "description": "WHAT_THIS_HOOK_DOES"
      }
    ]
  }
}
```

## External Script Template

Create `.claude/hooks/HOOK_NAME.sh`:

```bash
#!/bin/bash
# HOOK_NAME - DESCRIPTION
#
# Hook Event: HOOK_EVENT
# Matcher: TOOL_PATTERN
# Purpose: DETAILED_PURPOSE
#
# Exit codes:
#   0 - Success (continue)
#   1 - Error (log and continue)
#   2 - Block (PreToolUse/PermissionRequest only)

set -euo pipefail

# Read input from stdin
INPUT=$(cat)

# Parse with jq
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
# For Bash hooks:
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
# For Edit/Write hooks:
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Your logic here
# ...

# Exit appropriately
exit 0
```

Make executable:
```bash
chmod +x .claude/hooks/HOOK_NAME.sh
```

## Python Script Template

Create `.claude/hooks/HOOK_NAME.py`:

```python
#!/usr/bin/env python3
"""
HOOK_NAME - DESCRIPTION

Hook Event: HOOK_EVENT
Matcher: TOOL_PATTERN
"""
import json
import sys
import os

def main():
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # For Bash hooks
        command = tool_input.get('command', '')

        # For Edit/Write hooks
        file_path = tool_input.get('file_path', '')

        # Your logic here
        # ...

        # Exit 0 = success, 1 = error, 2 = block
        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

Make executable:
```bash
chmod +x .claude/hooks/HOOK_NAME.py
```

## Hook Events Quick Reference

| Event | When | Blocks | Typical Use |
|-------|------|--------|-------------|
| PreToolUse | Before tool | Yes | Validation, protection |
| PostToolUse | After tool | No | Formatting, logging |
| PermissionRequest | Permission dialog | Yes | Auto-allow/deny |
| UserPromptSubmit | Before processing | Yes | Prompt validation |
| Notification | Notification sent | No | Desktop alerts |
| Stop | Response complete | No | Cleanup, extraction |
| SubagentStop | Subagent done | No | Subagent results |
| SessionStart | Session begins | No | Setup, state |
| SessionEnd | Session ends | No | Cleanup, reports |

## Matcher Patterns

```
*              # All tools
Bash           # Only Bash
Edit|Write     # Edit or Write
Read|Grep|Glob # Multiple tools
""             # Empty (for events without tools)
```
