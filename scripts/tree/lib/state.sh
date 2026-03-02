#!/bin/bash
#
# Script: lib/state.sh
# Purpose: Build state persistence for resume capability
# Created: 2026-01-28
# Description: Save and restore build state for interrupted operations

# Dependencies: lib/common.sh (print_* functions), jq
# Required variables: BUILD_STATE_FILE

# Save current build state to JSON file
# Usage: save_build_state dev_branch total_features completed_json failed_worktree remaining_json
save_build_state() {
    local dev_branch=$1
    local total_features=$2
    local completed_worktrees_json=$3
    local failed_worktree=$4
    local remaining_features_json=$5

    mkdir -p "$(dirname "$BUILD_STATE_FILE")"

    # Use jq with --slurpfile for safe JSON handling (avoids bash expansion issues
    # with special characters in feature names that --argjson would have)
    local tmp_completed tmp_remaining
    tmp_completed=$(mktemp)
    tmp_remaining=$(mktemp)
    trap 'rm -f "$tmp_completed" "$tmp_remaining"' RETURN
    echo "${completed_worktrees_json:-[]}" > "$tmp_completed"
    echo "${remaining_features_json:-[]}" > "$tmp_remaining"

    jq -n \
        --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg db "$dev_branch" \
        --argjson tf "$total_features" \
        --slurpfile cw "$tmp_completed" \
        --arg fw "$failed_worktree" \
        --slurpfile rf "$tmp_remaining" \
        '{
            timestamp: $ts,
            dev_branch: $db,
            total_features: $tf,
            completed_worktrees: $cw[0],
            failed_worktree: $fw,
            remaining_features: $rf[0]
        }' > "$BUILD_STATE_FILE"
    return $?
}

# Load build state from JSON file
# Usage: load_build_state
# Returns 0 if valid state exists, 1 otherwise
load_build_state() {
    if [ ! -f "$BUILD_STATE_FILE" ]; then
        return 1
    fi

    # Validate JSON structure
    if ! jq empty "$BUILD_STATE_FILE" 2>/dev/null; then
        print_warning "Build state file is corrupted"

        if confirm_prompt "Would you like to delete it and start fresh?" "y"; then
            rm -f "$BUILD_STATE_FILE"
            print_success "Corrupted state file removed"
        fi
        return 1
    fi

    # Check if dev branch still exists (declare and assign separately)
    # Use refs/heads/ prefix to verify only local branches, not tags or commits
    local saved_branch
    saved_branch=$(jq -r '.dev_branch' "$BUILD_STATE_FILE" 2>/dev/null)
    if [ -n "$saved_branch" ] && ! git rev-parse --verify "refs/heads/$saved_branch" &>/dev/null; then
        print_warning "Saved dev branch no longer exists: $saved_branch"

        if confirm_prompt "Would you like to delete the stale state file?" "y"; then
            rm -f "$BUILD_STATE_FILE"
            print_success "Stale state file removed"
        fi
        return 1
    fi

    return 0
}

# Get a value from the build state
# Usage: get_build_state_value "key"
get_build_state_value() {
    local key=$1

    if [ ! -f "$BUILD_STATE_FILE" ]; then
        return 1
    fi

    jq -r --arg k "$key" '.[$k] // empty' "$BUILD_STATE_FILE" 2>/dev/null
}

# Get completed worktrees from build state as array
# Usage: get_build_state_completed
get_build_state_completed() {
    if [ ! -f "$BUILD_STATE_FILE" ]; then
        return 1
    fi

    jq -r '.completed_worktrees[]' "$BUILD_STATE_FILE" 2>/dev/null
}

# Get remaining features from build state as array
# Usage: get_build_state_remaining
get_build_state_remaining() {
    if [ ! -f "$BUILD_STATE_FILE" ]; then
        return 1
    fi

    jq -r '.remaining_features[]' "$BUILD_STATE_FILE" 2>/dev/null
}

# Clear build state file after successful completion
# Usage: clear_build_state
clear_build_state() {
    rm -f "$BUILD_STATE_FILE" 2>/dev/null
    return 0
}

# Check if there's a resumable build state
# Usage: has_resumable_state
has_resumable_state() {
    [ -f "$BUILD_STATE_FILE" ] && load_build_state
}
