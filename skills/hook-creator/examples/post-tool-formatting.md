# PostToolUse Formatting Hooks

Examples of hooks that format or process files after edits.

---

## Python Formatter (Ruff) - Venv-Aware

Auto-format Python files after edits using the project's virtual environment.
This ensures the correct version of ruff (with project-specific config) is used.

### Configuration

Add to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "tool == \"Edit\" && tool_input.file_path matches \"\\.py$\"",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/post-python-format.py\""
          }
        ],
        "description": "[frosty] Auto-format Python files with ruff (venv-aware)"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/post-python-format.py`:

```python
#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format Python files after edits.
Uses project's virtual environment to run the correct ruff version.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VENV_DIRS = [".venv", "venv", ".env", "env"]

def find_venv(project_dir: Path) -> Path | None:
    for name in VENV_DIRS:
        venv = project_dir / name
        if (venv / "bin" / "python").exists():
            return venv
    return None

def run_ruff(file_path: Path, project_dir: Path) -> None:
    # Try venv first
    venv = find_venv(project_dir)
    if venv:
        ruff = venv / "bin" / "ruff"
        if ruff.exists():
            subprocess.run([str(ruff), "format", str(file_path)], capture_output=True)
            return

    # Fallback to global
    if shutil.which("ruff"):
        subprocess.run(["ruff", "format", str(file_path)], capture_output=True)

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        json.dump(input_data, sys.stdout)
        sys.exit(0)

    file_path = Path(file_path)
    if not file_path.exists():
        json.dump(input_data, sys.stdout)
        sys.exit(0)

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", file_path.parent))
    run_ruff(file_path, project_dir)

    json.dump(input_data, sys.stdout)
    sys.exit(0)

if __name__ == "__main__":
    main()
```

```bash
chmod +x .claude/hooks/post-python-format.py
```

**Note:** The frosty plugin automatically syncs this hook to projects on session start.
You don't need to manually add it if using the plugin.

---

## JavaScript/TypeScript Prettier

Auto-format JS/TS files with Prettier.

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
            "command": "jq -r '.tool_input.file_path' | { read f; if echo \"$f\" | grep -qE '\\.(js|jsx|ts|tsx)$'; then npx prettier --write \"$f\" 2>/dev/null && echo \"[Hook] Formatted: $f\"; fi; }"
          }
        ],
        "description": "Auto-format JS/TS files with Prettier"
      }
    ]
  }
}
```

---

## Jinja2 Template Security Check

Check Jinja2 templates for security issues after edits.

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
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-jinja2-check.sh"
          }
        ],
        "description": "Check Jinja2 templates for security issues"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/post-jinja2-check.sh`:

```bash
#!/bin/bash
# post-jinja2-check.sh - Security check for Jinja2 templates

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process HTML files
if [[ ! "$FILE_PATH" =~ \.html$ ]]; then
    exit 0
fi

if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

WARNINGS=""

# Check for |safe filter (except tojson|safe)
if grep -n "|safe" "$FILE_PATH" 2>/dev/null | grep -v "tojson|safe" > /dev/null; then
    WARNINGS+="  - |safe filter found - ensure content is sanitized\n"
fi

# Check for autoescape false
if grep -n "autoescape false" "$FILE_PATH" 2>/dev/null > /dev/null; then
    WARNINGS+="  - autoescape disabled - potential XSS risk\n"
fi

# Check for inline scripts without nonce
if grep "<script" "$FILE_PATH" 2>/dev/null | grep -v "nonce=" | grep -v "src=" > /dev/null; then
    WARNINGS+="  - Inline script without nonce - add CSP nonce\n"
fi

if [[ -n "$WARNINGS" ]]; then
    echo "[Hook] Security warnings in $FILE_PATH:" >&2
    echo -e "$WARNINGS" >&2
fi

exit 0
```

```bash
chmod +x .claude/hooks/post-jinja2-check.sh
```

---

## Markdown Formatter

Auto-format markdown files and add missing language tags.

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
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-markdown-format.py"
          }
        ],
        "description": "Format markdown and add language tags"
      }
    ]
  }
}
```

### Script

Create `.claude/hooks/post-markdown-format.py`:

```python
#!/usr/bin/env python3
"""Format markdown files and detect missing language tags."""
import json
import sys
import re
import os

def detect_language(code):
    """Best-effort language detection."""
    s = code.strip()

    # JSON
    if re.search(r'^\s*[{\[]', s):
        try:
            json.loads(s)
            return 'json'
        except:
            pass

    # Python
    if re.search(r'^\s*(def|class|import|from)\s+', s, re.M):
        return 'python'

    # JavaScript
    if re.search(r'\b(function|const|let|var|=>)\b', s):
        return 'javascript'

    # Bash
    if re.search(r'^#!.*\b(bash|sh)\b|^\s*(if|for|while)\s+\[', s, re.M):
        return 'bash'

    # SQL
    if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE)\s+', s, re.I):
        return 'sql'

    return 'text'

def format_markdown(content):
    """Add language tags to bare code fences."""
    def add_lang(match):
        indent, info, body, closing = match.groups()
        if not info.strip():
            lang = detect_language(body)
            return f"{indent}```{lang}\n{body}{closing}\n"
        return match.group(0)

    pattern = r'(?ms)^([ \t]{0,3})```([^\n]*)\n(.*?)(\n\1```)\s*$'
    return re.sub(pattern, add_lang, content)

try:
    data = json.load(sys.stdin)
    path = data.get('tool_input', {}).get('file_path', '')

    if not path.endswith(('.md', '.mdx')) or not os.path.exists(path):
        sys.exit(0)

    with open(path, 'r') as f:
        content = f.read()

    formatted = format_markdown(content)

    if formatted != content:
        with open(path, 'w') as f:
            f.write(formatted)
        print(f"[Hook] Formatted: {path}")

except Exception as e:
    print(f"Hook error: {e}", file=sys.stderr)
    sys.exit(1)
```

```bash
chmod +x .claude/hooks/post-markdown-format.py
```

---

## Testing PostToolUse Hooks

1. Add the hook configuration
2. Ask Claude to edit a relevant file type
3. Verify the hook runs after the edit
4. Check the file was formatted/processed correctly

Example test:
```
User: "Add a print statement to main.py"
Expected: After edit, file is auto-formatted with ruff/black
```
