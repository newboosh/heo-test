#!/bin/bash
#
# UserPromptSubmit hook: capture the user's query for session recap.
#
# Reads JSON from stdin (the user prompt event), extracts the query
# text, and appends it to .context/session-queries.jsonl.
#
# Hook Event: UserPromptSubmit
# Mode: Non-blocking (always exits 0)
# Timeout: 5s
# Tag: [heo-test]
#

set -eu

# Read hook input from stdin
INPUT=$(cat 2>/dev/null) || INPUT=""

if [ -z "$INPUT" ]; then
    exit 0
fi

# Extract the user's prompt content
QUERY=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    # UserPromptSubmit provides the prompt in tool_input.content or tool_input.prompt
    prompt = (
        data.get('tool_input', {}).get('content', '')
        or data.get('tool_input', {}).get('prompt', '')
        or data.get('content', '')
        or ''
    )
    print(prompt)
except Exception:
    pass
" 2>/dev/null) || QUERY=""

if [ -z "$QUERY" ]; then
    exit 0
fi

# Determine context directory
CWD=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('cwd', ''))
except Exception:
    pass
" 2>/dev/null <<< "$INPUT") || CWD=""

if [ -z "$CWD" ]; then
    CWD="${CLAUDE_PROJECT_DIR:-.}"
fi

CONTEXT_DIR="$CWD/.context"
mkdir -p "$CONTEXT_DIR" 2>/dev/null || exit 0

# Append query as JSONL (one line per prompt submission)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
python3 -c "
import json, sys
entry = {
    'timestamp': sys.argv[1],
    'query': sys.argv[2][:2000],
}
print(json.dumps(entry))
" "$TIMESTAMP" "$QUERY" >> "$CONTEXT_DIR/session-queries.jsonl" 2>/dev/null || true

exit 0
