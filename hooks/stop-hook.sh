#!/bin/bash

# Ralph Wiggum Stop Hook
# Prevents session exit when a ralph-loop is active
# Feeds Claude's output back as input to continue the loop
#
# DESIGN: On transient errors (transcript parsing, missing fields), the hook
# still blocks exit and re-feeds the prompt. The state file is only deleted
# for intentional termination: max iterations reached or promise fulfilled.
# This makes the loop self-healing - transient failures don't kill it.

set -euo pipefail

# Verify jq is available (required for JSON output)
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found" >&2; exit 0; }

# Read hook input from stdin (advanced stop hook API)
HOOK_INPUT=$(cat)

# Check if ralph-loop is active
RALPH_STATE_FILE=".claude/ralph-loop.local.md"

if [[ ! -f "$RALPH_STATE_FILE" ]]; then
  # No active loop - allow exit
  exit 0
fi

# Parse markdown frontmatter (YAML between ---) and extract values
# Use || true to prevent set -e from exiting on grep/sed failures
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$RALPH_STATE_FILE" || true)
ITERATION=$(echo "$FRONTMATTER" | grep '^iteration:' | sed 's/iteration: *//' || true)
MAX_ITERATIONS=$(echo "$FRONTMATTER" | grep '^max_iterations:' | sed 's/max_iterations: *//' || true)
# Extract completion_promise and strip surrounding quotes if present
COMPLETION_PROMISE=$(echo "$FRONTMATTER" | grep '^completion_promise:' | sed 's/completion_promise: *//' | sed 's/^"\(.*\)"$/\1/' || true)

# --- Helper: upsert a key in YAML frontmatter (insert if missing, replace if present) ---
# Only accepts numeric values to avoid sed injection via &, /, or \ characters.
upsert_frontmatter() {
  local key="$1" value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "⚠️  upsert_frontmatter: rejecting non-numeric value '$value' for key '$key'" >&2
    return 1
  fi
  local tmp
  tmp=$(mktemp "${RALPH_STATE_FILE}.XXXXXXXX") || return 1
  if grep -q "^${key}:" "$RALPH_STATE_FILE" 2>/dev/null; then
    sed '/^---$/,/^---$/s/^'"${key}"': .*/'"${key}"': '"${value}"'/' "$RALPH_STATE_FILE" > "$tmp"
  else
    awk -v k="$key" -v v="$value" '
      /^---$/{
        c++
        print
        if(c==1){print k": "v}
        next
      }
      {print}
    ' "$RALPH_STATE_FILE" > "$tmp"
  fi
  mv "$tmp" "$RALPH_STATE_FILE"
}

# --- Helper: block exit and re-feed the prompt (used for error recovery) ---
block_with_prompt() {
  local error_msg="${1:-}"
  local iteration="${2:-0}"
  local next_iteration="${3:-$((iteration + 1))}"

  # Extract prompt from state file
  local prompt_text
  prompt_text=$(awk '/^---$/{i++; next} i>=2' "$RALPH_STATE_FILE" 2>/dev/null | sed '1{/^$/d;}' || true)

  if [[ -z "$prompt_text" ]]; then
    # State file is truly corrupted (no prompt) - this is the one case we give up
    echo "⚠️  Ralph loop: State file has no prompt text, cannot recover. Stopping." >&2
    rm -f "$RALPH_STATE_FILE"
    exit 0
  fi

  # Log the error but keep going
  if [[ -n "$error_msg" ]]; then
    echo "⚠️  Ralph loop: $error_msg (recovering, iteration $iteration)" >&2
  fi

  local sys_msg="🔄 Ralph iteration $next_iteration (recovered from error) | Loop continues"
  if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
    sys_msg="🔄 Ralph iteration $next_iteration (recovered) | To stop: output <promise>$COMPLETION_PROMISE</promise> (ONLY when TRUE!)"
  fi

  jq -n \
    --arg prompt "$prompt_text" \
    --arg msg "$sys_msg" \
    '{
      "decision": "block",
      "reason": $prompt,
      "systemMessage": $msg
    }'
  exit 0
}

# Validate numeric fields - recover instead of dying
if [[ ! "$ITERATION" =~ ^[0-9]+$ ]]; then
  # Try to default to 1 instead of killing the loop
  echo "⚠️  Ralph loop: iteration field invalid ('$ITERATION'), defaulting to 1" >&2
  ITERATION=1
  # Fix the state file (upsert handles missing key)
  upsert_frontmatter "iteration" "1" || true
fi

if [[ ! "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "⚠️  Ralph loop: max_iterations field invalid ('$MAX_ITERATIONS'), defaulting to 0 (unlimited)" >&2
  MAX_ITERATIONS=0
  # Fix the state file (upsert handles missing key)
  upsert_frontmatter "max_iterations" "0" || true
fi

# Check if max iterations reached (INTENTIONAL termination - delete state file)
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  echo "🛑 Ralph loop: Max iterations ($MAX_ITERATIONS) reached." >&2
  rm -f "$RALPH_STATE_FILE"
  exit 0
fi

# Increment iteration EARLY (before transcript parsing which may fail)
# This ensures the counter always advances, even on error recovery paths
NEXT_ITERATION=$((ITERATION + 1))
if ! upsert_frontmatter "iteration" "$NEXT_ITERATION" 2>/dev/null; then
  block_with_prompt "Failed to update iteration in state file" "$ITERATION" "$NEXT_ITERATION"
fi

# Get transcript path from hook input - recover on failure
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path' 2>/dev/null || true)

# Handle missing/null transcript path - recover by re-feeding prompt
if [[ -z "$TRANSCRIPT_PATH" ]] || [[ "$TRANSCRIPT_PATH" == "null" ]]; then
  block_with_prompt "No transcript_path in hook input" "$ITERATION" "$NEXT_ITERATION"
fi

if [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  block_with_prompt "Transcript file not found: $TRANSCRIPT_PATH" "$ITERATION" "$NEXT_ITERATION"
fi

# Extract last assistant message (robust to spacing/ordering in JSONL)
# NOTE: jq processes JSONL sequentially and stops at malformed lines.
# If the transcript is truncated/corrupted, this may return an earlier
# assistant message rather than the actual last one. This is acceptable
# because transcripts are machine-generated by Claude Code.
LAST_LINE=$(jq -c 'select(.role == "assistant")' "$TRANSCRIPT_PATH" 2>/dev/null | tail -1 || true)
if [[ -z "$LAST_LINE" ]]; then
  block_with_prompt "No assistant messages in transcript" "$ITERATION" "$NEXT_ITERATION"
fi

# Parse JSON - extract text content
LAST_OUTPUT=""
LAST_OUTPUT=$(echo "$LAST_LINE" | jq -r '
  .message.content |
  map(select(.type == "text")) |
  map(.text) |
  join("\n")
' 2>/dev/null || true)

if [[ -z "$LAST_OUTPUT" ]]; then
  # No text content in response (maybe only tool calls) - still continue the loop
  block_with_prompt "Assistant message had no text content" "$ITERATION" "$NEXT_ITERATION"
fi

# Check for completion promise (only if set)
if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  # Extract text from <promise> tags using Perl for multiline support
  # -0777 slurps entire input, -ne only prints on match (avoids returning
  # the entire input when no <promise> tags exist)
  PROMISE_TEXT=$(echo "$LAST_OUTPUT" | perl -0777 -ne 'if(/<promise>(.*?)<\/promise>/s){$t=$1; $t=~s/^\s+|\s+$//g; $t=~s/\s+/ /g; print $t}' 2>/dev/null || echo "")

  # Use = for literal string comparison (not pattern matching)
  # == in [[ ]] does glob pattern matching which breaks with *, ?, [ characters
  if [[ -n "$PROMISE_TEXT" ]] && [[ "$PROMISE_TEXT" = "$COMPLETION_PROMISE" ]]; then
    # INTENTIONAL termination - promise fulfilled - delete state file
    echo "✅ Ralph loop: Detected <promise>$COMPLETION_PROMISE</promise>" >&2
    rm -f "$RALPH_STATE_FILE"
    exit 0
  fi
fi

# Not complete - continue loop with SAME PROMPT
# (NEXT_ITERATION was already computed and state file updated above)

# Extract prompt (everything after the closing ---)
PROMPT_TEXT=$(awk '/^---$/{i++; next} i>=2' "$RALPH_STATE_FILE" | sed '1{/^$/d;}')

if [[ -z "$PROMPT_TEXT" ]]; then
  echo "⚠️  Ralph loop: State file has no prompt text, cannot continue. Stopping." >&2
  rm -f "$RALPH_STATE_FILE"
  exit 0
fi

# Build system message with iteration count and completion promise info
if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  SYSTEM_MSG="🔄 Ralph iteration $NEXT_ITERATION | To stop: output <promise>$COMPLETION_PROMISE</promise> (ONLY when statement is TRUE - do not lie to exit!)"
else
  SYSTEM_MSG="🔄 Ralph iteration $NEXT_ITERATION | No completion promise set - loop runs infinitely"
fi

# Output JSON to block the stop and feed prompt back
jq -n \
  --arg prompt "$PROMPT_TEXT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'

exit 0
