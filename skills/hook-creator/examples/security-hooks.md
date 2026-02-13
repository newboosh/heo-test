# Security and Protection Hooks

Examples of hooks that protect sensitive files and enforce security policies.

---

## Sensitive File Protector

Block edits to sensitive files like `.env`, credentials, and lock files.

### Configuration

Add to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-sensitive-files.sh"
          }
        ],
        "description": "Protect sensitive files from modification"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/protect-sensitive-files.sh`:

```bash
#!/bin/bash
# protect-sensitive-files.sh - Block edits to sensitive files
#
# Exit 2 = block the edit

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Define protected patterns
PROTECTED_PATTERNS=(
    "\.env$"
    "\.env\."
    "credentials"
    "secrets"
    "\.pem$"
    "\.key$"
    "package-lock\.json$"
    "yarn\.lock$"
    "poetry\.lock$"
    "Pipfile\.lock$"
    "\.git/"
    "node_modules/"
    "__pycache__/"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" =~ $pattern ]]; then
        echo "[Hook] BLOCKED: Cannot modify protected file: $FILE_PATH" >&2
        echo "[Hook] This file matches protected pattern: $pattern" >&2
        exit 2
    fi
done

exit 0
```

```bash
chmod +x .claude/hooks/protect-sensitive-files.sh
```

---

## Inline Sensitive File Protection

Simpler inline version without external script.

### Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"import json,sys;d=json.load(sys.stdin);p=d.get('tool_input',{}).get('file_path','');sys.exit(2 if any(x in p for x in ['.env','.pem','.key','credentials','secrets','.git/','package-lock.json']) else 0)\""
          }
        ],
        "description": "Protect sensitive files (inline)"
      }
    ]
  }
}
```

---

## Directory Boundary Enforcer

Prevent edits outside the project directory.

### Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/enforce-boundaries.sh"
          }
        ],
        "description": "Prevent access outside project directory"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/enforce-boundaries.sh`:

```bash
#!/bin/bash
# enforce-boundaries.sh - Block access outside project directory

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

case "$TOOL_NAME" in
    Edit|Write)
        PATH_TO_CHECK=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
        ;;
    Bash)
        # For Bash, we can't easily check all paths in a command
        # Just block obvious escapes
        COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
        if [[ "$COMMAND" =~ (cd[[:space:]]+)?(/|~|\.\./)+ ]]; then
            # Allow if it's within project dir
            RESOLVED=$(cd "$CLAUDE_PROJECT_DIR" && realpath -m "${BASH_REMATCH[0]}" 2>/dev/null || echo "")
            if [[ -n "$RESOLVED" ]] && [[ ! "$RESOLVED" =~ ^"$CLAUDE_PROJECT_DIR" ]]; then
                echo "[Hook] WARNING: Command may access files outside project" >&2
            fi
        fi
        exit 0
        ;;
    *)
        exit 0
        ;;
esac

if [[ -z "$PATH_TO_CHECK" ]]; then
    exit 0
fi

# Resolve to absolute path
RESOLVED=$(realpath -m "$PATH_TO_CHECK" 2>/dev/null || echo "$PATH_TO_CHECK")

# Check if within project directory
if [[ ! "$RESOLVED" =~ ^"$CLAUDE_PROJECT_DIR" ]]; then
    echo "[Hook] BLOCKED: Cannot modify files outside project directory" >&2
    echo "[Hook] Path: $PATH_TO_CHECK" >&2
    echo "[Hook] Project: $CLAUDE_PROJECT_DIR" >&2
    exit 2
fi

exit 0
```

```bash
chmod +x .claude/hooks/enforce-boundaries.sh
```

---

## Secret Detection Scanner

Scan edited files for accidentally committed secrets.

### Configuration

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/scan-secrets.sh"
          }
        ],
        "description": "Scan for accidentally committed secrets"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/scan-secrets.sh`:

```bash
#!/bin/bash
# scan-secrets.sh - Scan for secrets in edited files

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Skip binary and non-text files
if file "$FILE_PATH" | grep -qv text; then
    exit 0
fi

WARNINGS=""

# Check for common secret patterns
SECRET_PATTERNS=(
    'AKIA[0-9A-Z]{16}'                    # AWS Access Key
    'sk-[a-zA-Z0-9]{48}'                  # OpenAI API Key
    'ghp_[a-zA-Z0-9]{36}'                 # GitHub Personal Access Token
    'sk_live_[a-zA-Z0-9]{24}'             # Stripe Secret Key
    'password\s*=\s*["\x27][^"\x27]+'     # Hardcoded password
    'api[_-]?key\s*=\s*["\x27][^"\x27]+'  # API key assignment
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -qE "$pattern" "$FILE_PATH" 2>/dev/null; then
        WARNINGS+="  - Potential secret detected (pattern: ${pattern:0:20}...)\n"
    fi
done

if [[ -n "$WARNINGS" ]]; then
    echo "[Hook] SECRET WARNING in $FILE_PATH:" >&2
    echo -e "$WARNINGS" >&2
    echo "[Hook] Review before committing!" >&2
fi

exit 0
```

```bash
chmod +x .claude/hooks/scan-secrets.sh
```

---

## Permission Request Auto-Handler

Auto-deny certain permission requests.

### Configuration

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.permission_type // empty' | { read perm; if [ \"$perm\" = \"network\" ]; then echo '[Hook] Auto-denied network permission' >&2; exit 2; fi; exit 0; }"
          }
        ],
        "description": "Auto-deny network permission requests"
      }
    ]
  }
}
```

---

## Testing Security Hooks

1. **File Protection**: Try to edit `.env` or a protected file
2. **Boundary Enforcement**: Try to edit `/etc/hosts` or `~/`
3. **Secret Detection**: Add a fake API key to a file
4. **Permission Auto-Handler**: Trigger a permission request

Example tests:
```
# Test file protection
User: "Add a new variable to .env"
Expected: Hook blocks with "Cannot modify protected file"

# Test secret detection
User: "Add this API key: sk-abc123... to config.py"
Expected: Warning about potential secret detected
```
