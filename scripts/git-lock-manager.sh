#!/bin/bash

# Git Lock Manager - Advanced Multi-Worktree Lock Coordination
# Provides per-worktree and global lock management for concurrent git operations

set -e

# ==============================================================================
# Configuration
# ==============================================================================

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
GIT_LOCKS_DIR="$WORKSPACE_ROOT/.git/.git-locks"
GIT_GLOBAL_LOCK="$GIT_LOCKS_DIR/global.lock"
GIT_OPERATION_LOG="$WORKSPACE_ROOT/.git/.git-operations.log"

# Lock timeout in seconds
LOCK_TIMEOUT=30

# ==============================================================================
# Initialization
# ==============================================================================

# Create lock directory structure
init_lock_system() {
    mkdir -p "$GIT_LOCKS_DIR"

    # Create global lock file if it doesn't exist
    touch "$GIT_GLOBAL_LOCK" 2>/dev/null || true

    # Initialize log
    touch "$GIT_OPERATION_LOG" 2>/dev/null || true
}

# ==============================================================================
# Lock Scope Determination
# ==============================================================================

# Determine if a git operation requires global or worktree-specific lock
#
# Global operations affect shared repository state (refs, objects)
# Worktree operations only affect specific worktree state
#
# Args:
#   $@ - Git command and arguments
# Returns:
#   "global" or "worktree"
determine_lock_scope() {
    local git_cmd="$1"

    case "$git_cmd" in
        # Global lock required - affects shared state
        merge|rebase|pull|fetch|push)
            echo "global"
            ;;

        # Global lock required - modifies worktree list
        worktree)
            echo "global"
            ;;

        # Global lock required - may affect multiple refs
        checkout)
            # Branch checkout affects refs
            if [[ "$*" =~ -b|--orphan ]]; then
                echo "global"
            else
                echo "worktree"
            fi
            ;;

        # Worktree lock sufficient - local changes only
        add|commit|status|diff|stash|reset)
            echo "worktree"
            ;;

        # Branch operations
        branch)
            # Creating/deleting branches is global
            if [[ "$*" =~ -d|-D|-m|-M ]]; then
                echo "global"
            else
                echo "worktree"
            fi
            ;;

        # Default to global for safety
        *)
            echo "global"
            ;;
    esac
}

# ==============================================================================
# Worktree Lock Path Management
# ==============================================================================

# Get lock file path for current worktree
#
# Returns:
#   Path to worktree-specific lock file
get_worktree_lock() {
    local worktree_path=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo "$WORKSPACE_ROOT/.git")
    local worktree_name=$(basename "$(dirname "$worktree_path")" 2>/dev/null || echo "main")

    # Sanitize worktree name for filename
    worktree_name=$(echo "$worktree_name" | sed 's/[^a-zA-Z0-9_-]/_/g')

    local lock_file="$GIT_LOCKS_DIR/${worktree_name}.lock"
    echo "$lock_file"
}

# ==============================================================================
# Lock Acquisition
# ==============================================================================

# Acquire a lock with timeout using flock
#
# Args:
#   $1 - Lock file path
#   $2 - Lock scope (global/worktree)
#   $3 - Operation description
# Returns:
#   0 on success, 1 on timeout
acquire_lock() {
    local lock_file="$1"
    local scope="$2"
    local operation="$3"

    # Ensure lock file exists
    touch "$lock_file" 2>/dev/null || return 1

    log_lock_event "acquire_attempt" "$scope" "$operation" "$lock_file"

    # Try to acquire lock with timeout
    if command -v flock &> /dev/null; then
        if flock -x -w "$LOCK_TIMEOUT" 200; then
            log_lock_event "acquire_success" "$scope" "$operation" "$lock_file"
            return 0
        else
            log_lock_event "acquire_timeout" "$scope" "$operation" "$lock_file"
            return 1
        fi
    else
        # Fallback: no flock available
        log_lock_event "acquire_noflock" "$scope" "$operation" "$lock_file"
        return 0
    fi

    return 1
}

# ==============================================================================
# Safe Git Wrapper with Intelligent Lock Selection
# ==============================================================================

# Execute git command with appropriate lock scope
#
# Automatically determines if global or worktree lock is needed
# and acquires the appropriate lock before execution
#
# Args:
#   $@ - Git command and arguments
# Returns:
#   Exit code from git command
safe_git_advanced() {
    local git_cmd="$@"
    local first_arg="${1}"

    # Determine lock scope
    local scope=$(determine_lock_scope "$first_arg" "$@")

    # Get appropriate lock file
    local lock_file
    if [ "$scope" = "global" ]; then
        lock_file="$GIT_GLOBAL_LOCK"
    else
        lock_file=$(get_worktree_lock)
        touch "$lock_file" 2>/dev/null || lock_file="$GIT_GLOBAL_LOCK"
    fi

    log_lock_event "operation_start" "$scope" "git $first_arg" "$lock_file"

    # Execute with lock
    (
        if ! acquire_lock "$lock_file" "$scope" "git $first_arg"; then
            echo "Error: Failed to acquire $scope lock after ${LOCK_TIMEOUT}s for: git $first_arg" >&2
            return 1
        fi

        # Run git command
        git "$@"
        local exit_code=$?

        log_lock_event "operation_complete" "$scope" "git $first_arg (exit: $exit_code)" "$lock_file"

        return $exit_code
    ) 200>"$lock_file"

    return $?
}

# ==============================================================================
# Logging
# ==============================================================================

# Log lock events for monitoring and debugging
#
# Args:
#   $1 - Event type (acquire_attempt|acquire_success|acquire_timeout|operation_start|operation_complete)
#   $2 - Lock scope (global|worktree)
#   $3 - Operation description
#   $4 - Lock file path
log_lock_event() {
    local event_type="$1"
    local scope="$2"
    local operation="$3"
    local lock_file="$4"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S.%3N")

    # Structured log format for easy parsing
    echo "[$timestamp] $event_type | scope=$scope | lock=$lock_file | op=$operation" >> "$GIT_OPERATION_LOG"
}

# ==============================================================================
# Lock Status & Diagnostics
# ==============================================================================

# Show current lock status
show_lock_status() {
    echo "=== Git Lock Status ==="
    echo ""
    echo "Global Lock: $GIT_GLOBAL_LOCK"

    if [ -f "$GIT_GLOBAL_LOCK" ]; then
        local size=$(stat -c %s "$GIT_GLOBAL_LOCK" 2>/dev/null || stat -f %z "$GIT_GLOBAL_LOCK" 2>/dev/null)
        echo "  Status: Exists (${size} bytes)"

        # Check if locked
        if command -v flock &> /dev/null; then
            if flock -n -x "$GIT_GLOBAL_LOCK" true 2>/dev/null; then
                echo "  State: Available"
            else
                echo "  State: LOCKED"
            fi
        fi
    else
        echo "  Status: Not created"
    fi

    echo ""
    echo "Worktree Locks:"

    if [ -d "$GIT_LOCKS_DIR" ]; then
        local count=0
        for lock in "$GIT_LOCKS_DIR"/*.lock; do
            if [ -f "$lock" ] && [ "$lock" != "$GIT_GLOBAL_LOCK" ]; then
                count=$((count + 1))
                local name=$(basename "$lock" .lock)
                echo "  $name"

                # Check if locked
                if command -v flock &> /dev/null; then
                    if flock -n -x "$lock" true 2>/dev/null; then
                        echo "    State: Available"
                    else
                        echo "    State: LOCKED"
                    fi
                fi
            fi
        done

        if [ $count -eq 0 ]; then
            echo "  (none)"
        fi
    else
        echo "  Lock directory not initialized"
    fi

    echo ""
    echo "Recent Operations (last 10):"
    if [ -f "$GIT_OPERATION_LOG" ]; then
        tail -10 "$GIT_OPERATION_LOG" | sed 's/^/  /'
    else
        echo "  (no log file)"
    fi
}

# Clean up stale lock files
cleanup_locks() {
    local cleaned=0

    if [ -d "$GIT_LOCKS_DIR" ]; then
        for lock in "$GIT_LOCKS_DIR"/*.lock; do
            if [ -f "$lock" ]; then
                # Try to acquire non-blocking lock
                if command -v flock &> /dev/null; then
                    if flock -n -x "$lock" true 2>/dev/null; then
                        # Lock was available, likely stale
                        echo "Cleaned: $(basename "$lock")"
                        cleaned=$((cleaned + 1))
                    fi
                fi
            fi
        done
    fi

    echo "Cleaned $cleaned lock files"
}

# ==============================================================================
# Initialization on sourcing
# ==============================================================================

# Initialize lock system when script is sourced
init_lock_system

# Export functions for use in other scripts
export -f determine_lock_scope
export -f get_worktree_lock
export -f safe_git_advanced
export -f show_lock_status
export -f cleanup_locks
