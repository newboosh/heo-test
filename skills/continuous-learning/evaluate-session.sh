#!/bin/bash
# Continuous Learning - Session Evaluator
# Runs on Stop hook to extract reusable patterns from Claude Code sessions
#
# Why Stop hook instead of UserPromptSubmit:
# - Stop runs once at session end (lightweight)
# - UserPromptSubmit runs every message (heavy, adds latency)
#
# Patterns to detect: error_resolution, debugging_techniques, workarounds, project_specific
# Patterns to ignore: simple_typos, one_time_fixes, external_api_issues
# Extracted skills saved to: .claude/skills/learned/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
LEARNED_SKILLS_PATH="$PROJECT_ROOT/.claude/skills/learned"
MIN_SESSION_LENGTH=10

# Load config if exists
if [ -f "$CONFIG_FILE" ]; then
  MIN_SESSION_LENGTH=$(jq -r '.min_session_length // 10' "$CONFIG_FILE")
  LEARNED_SKILLS_PATH_CONFIG=$(jq -r '.learned_skills_path // ".claude/skills/learned/"' "$CONFIG_FILE")
  # Handle relative paths
  if [[ ! "$LEARNED_SKILLS_PATH_CONFIG" = /* ]]; then
    LEARNED_SKILLS_PATH="$PROJECT_ROOT/$LEARNED_SKILLS_PATH_CONFIG"
  else
    LEARNED_SKILLS_PATH="$LEARNED_SKILLS_PATH_CONFIG"
  fi
fi

# Ensure learned skills directory exists
mkdir -p "$LEARNED_SKILLS_PATH"

# Get transcript path from environment (set by Claude Code)
transcript_path="${CLAUDE_TRANSCRIPT_PATH:-}"

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
  exit 0
fi

# Count messages in session
message_count=$(grep -c '"type":"user"' "$transcript_path" 2>/dev/null || echo "0")

# Skip short sessions
if [ "$message_count" -lt "$MIN_SESSION_LENGTH" ]; then
  echo "[ContinuousLearning] Session too short ($message_count messages), skipping" >&2
  exit 0
fi

# Signal to Claude that session should be evaluated for extractable patterns
echo "[ContinuousLearning] Session has $message_count messages - evaluate for extractable patterns" >&2
echo "[ContinuousLearning] Save learned skills to: $LEARNED_SKILLS_PATH" >&2

# Look for error resolution patterns
if grep -q '"error"' "$transcript_path" 2>/dev/null; then
  echo "[ContinuousLearning] Errors detected - check for resolution patterns" >&2
fi

# Look for repeated corrections
correction_count=$(grep -c '"correction"' "$transcript_path" 2>/dev/null || echo "0")
if [ "$correction_count" -gt 2 ]; then
  echo "[ContinuousLearning] Multiple corrections detected - consider extracting user preferences" >&2
fi
