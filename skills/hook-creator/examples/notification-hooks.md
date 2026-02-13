# Notification and Lifecycle Hooks

Examples of hooks for notifications and session lifecycle events.

---

## Desktop Notification (macOS)

Send desktop notification when Claude needs input.

### Configuration

Add to `~/.claude/settings.json` (user-wide):

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
          }
        ],
        "description": "Desktop notification when awaiting input"
      }
    ]
  }
}
```

---

## Desktop Notification (Linux)

Using `notify-send` for Linux systems.

### Configuration

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' 'Awaiting your input' --urgency=normal"
          }
        ],
        "description": "Desktop notification for Linux"
      }
    ]
  }
}
```

---

## Sound Alert

Play a sound when Claude completes a response.

### Configuration (macOS)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "afplay /System/Library/Sounds/Glass.aiff"
          }
        ],
        "description": "Play sound when response complete"
      }
    ]
  }
}
```

### Configuration (Linux)

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || true"
          }
        ],
        "description": "Play sound when response complete"
      }
    ]
  }
}
```

---

## Session Start Logger

Log session starts for auditing.

### Configuration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[$(date '+%Y-%m-%d %H:%M:%S')] Session started: $CLAUDE_SESSION_ID in $CLAUDE_PROJECT_DIR\" >> \"$HOME/.claude/session-audit.log\""
          }
        ],
        "description": "Log session starts"
      }
    ]
  }
}
```

---

## Session End Cleanup

Clean up temporary files when session ends.

### Configuration

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "rm -f /tmp/claude-temp-$CLAUDE_SESSION_ID-* 2>/dev/null || true"
          }
        ],
        "description": "Clean up session temp files"
      }
    ]
  }
}
```

---

## Subagent Completion Logger

Log when subagent tasks complete.

### Configuration

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"[Subagent] \\(.agent_type // \"unknown\"): \\(.status // \"completed\")\"'"
          }
        ],
        "description": "Log subagent task completion"
      }
    ]
  }
}
```

---

## Pre-Compact Context Saver

Save context summary before compact operation.

### Configuration

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"[$(date '+%Y-%m-%d %H:%M:%S')] Compact triggered for session $CLAUDE_SESSION_ID\" >> \"$HOME/.claude/compact.log\""
          }
        ],
        "description": "Log compact operations"
      }
    ]
  }
}
```

---

## Stop Hook: Pattern Extraction

Extract learned patterns at end of response (see continuous-learning skill).

### Configuration

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/extract-patterns.sh"
          }
        ],
        "description": "Extract reusable patterns from session"
      }
    ]
  }
}
```

---

## Testing Notification/Lifecycle Hooks

1. Add the hook configuration
2. Trigger the relevant event:
   - **Notification**: Let Claude finish and wait for input
   - **Stop**: Complete any Claude response
   - **SessionStart**: Start a new Claude session
   - **SessionEnd**: Exit Claude Code cleanly
3. Verify the hook executed (check logs, notifications, etc.)
