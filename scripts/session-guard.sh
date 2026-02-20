#!/bin/bash
# Session guard check for bash scripts.
#
# Source this file and call: check_session_guard <group_name> <my_skill_id>
#
# Returns 0 if this skill should run, returns 1 if it should not.
# The caller decides what to do on return 1 (typically: exit 0).
# Fails open on all error conditions (missing file, missing jq, bad JSON).
#
# Usage:
#   source "${CLAUDE_PLUGIN_ROOT}/scripts/session-guard.sh"
#   check_session_guard "session-end-learning" "continuous-learning" || exit 0

check_session_guard() {
    local group_name="$1"
    local my_skill_id="$2"
    local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    local config_file="$project_root/.claude/session-config.json"

    # Fail open: missing arguments, missing config, missing jq
    [ -z "$group_name" ] || [ -z "$my_skill_id" ] && return 0
    [ ! -f "$config_file" ] && return 0
    command -v jq &> /dev/null || return 0

    # Read the selected skill for our conflict group
    local selected
    selected=$(jq -r ".conflict_groups.\"${group_name}\".selected // \"\"" "$config_file" 2>/dev/null)

    # Fail open: if we can't read the config or field is empty
    [ -z "$selected" ] && return 0

    # If we are NOT the selected skill, return 1 (caller decides action)
    if [ "$selected" != "$my_skill_id" ]; then
        echo "[SessionGuard] $my_skill_id skipped: $selected is active (group: $group_name)" >&2
        return 1
    fi

    # We are the selected skill, proceed
    return 0
}
