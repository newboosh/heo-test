#!/bin/bash
# Strategic Compact Suggester
# Runs on PreToolUse to suggest manual compaction at logical intervals
#
# Why manual over auto-compact:
# - Auto-compact happens at arbitrary points, often mid-task
# - Strategic compacting preserves context through logical phases
# - Compact after exploration, before execution
# - Compact after completing a milestone, before starting next
#
# Criteria for suggesting compact:
# - Large number of tool calls made (threshold: 50)
# - Periodic reminders every 25 calls after threshold

# Track tool call count (increment in a temp file per session)
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
COUNTER_FILE="/tmp/claude-tool-count-$SESSION_ID"
THRESHOLD=${COMPACT_THRESHOLD:-50}
REMINDER_INTERVAL=25

# Initialize or increment counter
if [ -f "$COUNTER_FILE" ]; then
  count=$(cat "$COUNTER_FILE")
  count=$((count + 1))
  echo "$count" > "$COUNTER_FILE"
else
  echo "1" > "$COUNTER_FILE"
  count=1
fi

# Suggest compact after threshold tool calls
if [ "$count" -eq "$THRESHOLD" ]; then
  echo "[StrategicCompact] $THRESHOLD tool calls reached - consider /compact if transitioning phases" >&2
  echo "[StrategicCompact] Good times to compact:" >&2
  echo "[StrategicCompact]   - After planning, before implementation" >&2
  echo "[StrategicCompact]   - After debugging, before next task" >&2
  echo "[StrategicCompact]   - After completing a feature" >&2
fi

# Suggest at regular intervals after threshold
if [ "$count" -gt "$THRESHOLD" ] && [ $((count % REMINDER_INTERVAL)) -eq 0 ]; then
  echo "[StrategicCompact] $count tool calls - consider /compact if context is stale" >&2
fi

# High watermark warning
if [ "$count" -eq 100 ]; then
  echo "[StrategicCompact] 100 tool calls - strongly recommend /compact soon" >&2
fi

if [ "$count" -eq 150 ]; then
  echo "[StrategicCompact] WARNING: 150 tool calls - context likely saturated, /compact recommended" >&2
fi
