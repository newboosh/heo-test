#!/bin/bash
#
# Stop hook: recap the original user query and session work summary.
#
# Reads .context/session-queries.jsonl (written by capture-query.sh)
# and outputs a human-readable recap to stderr so the model is
# reminded of the original request before stopping.
#
# Hook Event: Stop
# Mode: Non-blocking (always exits 0)
# Timeout: 10s
# Tag: [heo-test]
#

set -eu

# Determine project directory
CWD="${CLAUDE_PROJECT_DIR:-.}"
CONTEXT_DIR="$CWD/.context"
QUERIES_FILE="$CONTEXT_DIR/session-queries.jsonl"

if [ ! -f "$QUERIES_FILE" ]; then
    exit 0
fi

# Read and format the recap
# Note: python writes recap to stderr (fd 3 preserves it through redirects)
python3 - "$QUERIES_FILE" <<'PYEOF' || exit 0
import json
import sys

queries_file = sys.argv[1]

try:
    queries = []
    with open(queries_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    q = entry.get("query", "").strip()
                    if q:
                        queries.append(q)
                except json.JSONDecodeError:
                    continue

    if not queries:
        sys.exit(0)

    print("\n[recap] Session queries:", file=sys.stderr)
    # Show first query prominently (original ask)
    print(f"  Original: {queries[0][:200]}", file=sys.stderr)

    # Show follow-ups if any (condensed)
    if len(queries) > 1:
        print(f"  Follow-ups: {len(queries) - 1}", file=sys.stderr)
        for q in queries[1:5]:  # Show up to 4 follow-ups
            print(f"    - {q[:120]}", file=sys.stderr)
        if len(queries) > 5:
            print(f"    ... and {len(queries) - 5} more", file=sys.stderr)

    print("", file=sys.stderr)

except Exception:
    pass

sys.exit(0)
PYEOF

exit 0
