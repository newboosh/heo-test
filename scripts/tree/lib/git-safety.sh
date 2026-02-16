#!/bin/bash
#
# Script: lib/git-safety.sh
# Purpose: Safe git operations with lock handling and concurrency protection
# Created: 2026-01-28
# Description: Provides safe_git wrapper with flock-based mutex and stale lock detection

# Dependencies: lib/common.sh (print_* functions)
# Required variables: WORKSPACE_ROOT, GIT_OPERATION_LOCK, GIT_OPERATION_LOG

# Check if a git lock file is stale
# Usage: is_lock_stale "/path/to/lock"
# Returns 0 if stale, 1 if not stale or file doesn't exist
is_lock_stale() {
    local lock_file=$1

    # File must exist to be stale
    if [ ! -f "$lock_file" ]; then
        return 1
    fi

    local stale_threshold="${TREE_STALE_LOCK_THRESHOLD:-60}"

    # Try to get threshold from config
    if type get_config_number &>/dev/null; then
        stale_threshold=$(get_config_number "behavior.stale_lock_threshold_seconds" "60")
    fi

    # Get lock file age in seconds (separate declaration from assignment to avoid masking return values)
    local current_time
    current_time=$(date +%s)
    local lock_time
    lock_time=$(stat -c %Y "$lock_file" 2>/dev/null || stat -f %m "$lock_file" 2>/dev/null || echo "0")
    local lock_age=$((current_time - lock_time))

    # Get lock file size
    local lock_size
    lock_size=$(stat -c %s "$lock_file" 2>/dev/null || stat -f %z "$lock_file" 2>/dev/null || echo "0")

    # Consider lock stale if:
    # 1. Older than threshold seconds AND
    # 2. File size is 0 (typical for git index.lock)
    if [ "$lock_age" -gt "$stale_threshold" ] && [ "$lock_size" -eq 0 ]; then
        return 0  # Stale
    fi
    return 1  # Not stale
}

# Handle git index.lock issues with enhanced stale lock detection
# Usage: wait_for_git_lock
# Returns 0 on success, 1 if lock persists
# Note: TREE_GIT_LOCK_TIMEOUT represents seconds of total wait time
wait_for_git_lock() {
    local max_wait="${TREE_GIT_LOCK_TIMEOUT:-30}"
    local wait_time=1
    local lock_file="$WORKSPACE_ROOT/.git/index.lock"

    # Try to get timeout from config
    if type get_config_number &>/dev/null; then
        max_wait=$(get_config_number "behavior.git_lock_timeout" "30")
    fi

    # Track elapsed time instead of attempt count
    local start_time
    start_time=$(date +%s)
    local elapsed=0

    while [ -f "$lock_file" ] && [ $elapsed -lt $max_wait ]; do
        # Check if lock is stale
        if is_lock_stale "$lock_file"; then
            print_warning "Stale git lock detected (>${TREE_STALE_LOCK_THRESHOLD:-60}s old), removing automatically..."
            rm -f "$lock_file" 2>/dev/null || {
                print_error "Failed to remove stale lock file. Please run: rm $lock_file"
                return 1
            }
            print_success "Stale lock removed successfully"
            return 0
        fi

        print_warning "Git lock detected, waiting ${wait_time}s (${elapsed}s/${max_wait}s elapsed)"
        sleep $wait_time

        # Exponential backoff: 1s, 2s, 4s, 8s, 16s (max)
        wait_time=$((wait_time * 2))
        [ $wait_time -gt 16 ] && wait_time=16

        # Update elapsed time
        local current_time
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
    done

    # Final check after timeout
    if [ -f "$lock_file" ]; then
        print_error "Git lock file persists after ${max_wait}s timeout. Please run: rm $lock_file"
        return 1
    fi
    return 0
}

# Log git operations for debugging and monitoring
# Usage: log_git_operation "description"
log_git_operation() {
    local operation=$1
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Create log directory if needed
    mkdir -p "$(dirname "$GIT_OPERATION_LOG")"

    echo "[$timestamp] $operation" >> "$GIT_OPERATION_LOG"
}

# Safe git wrapper with flock-based mutex for concurrent operation protection
# Supports error capture and verbose mode via TREE_VERBOSE environment variable
# Usage: safe_git <git_command_args>
safe_git() {
    local git_cmd=("$@")
    local operation_desc="${git_cmd[0]}"  # First word of command
    local verbose="${TREE_VERBOSE:-false}"

    # Check if flock is available
    if ! command -v flock &> /dev/null; then
        print_warning "flock not available, falling back to wait_for_git_lock"
        wait_for_git_lock || return 1

        # Run with or without output based on verbose mode
        if [ "$verbose" = "true" ]; then
            git "${git_cmd[@]}"
        else
            local git_output
            git_output=$(git "${git_cmd[@]}" 2>&1)
            local exit_code=$?

            # Show errors even in non-verbose mode
            if [ $exit_code -ne 0 ]; then
                echo "$git_output" >&2
            fi

            return $exit_code
        fi
        return $?
    fi

    # Create lock file if it doesn't exist
    touch "$GIT_OPERATION_LOCK" 2>/dev/null || {
        print_warning "Cannot create lock file, falling back to direct git"

        if [ "$verbose" = "true" ]; then
            git "${git_cmd[@]}"
        else
            local git_output
            git_output=$(git "${git_cmd[@]}" 2>&1)
            local exit_code=$?

            if [ $exit_code -ne 0 ]; then
                echo "$git_output" >&2
            fi

            return $exit_code
        fi
        return $?
    }

    log_git_operation "Acquiring lock for: git $operation_desc"

    # Acquire exclusive lock with timeout
    local lock_timeout="${TREE_GIT_LOCK_TIMEOUT:-30}"
    if type get_config_number &>/dev/null; then
        lock_timeout=$(get_config_number "behavior.git_lock_timeout" "30")
    fi

    (
        if ! flock -x -w "$lock_timeout" 200; then
            print_error "Failed to acquire git operation lock after ${lock_timeout}s for: git $operation_desc"
            log_git_operation "Lock acquisition FAILED (timeout) for: git $operation_desc"
            return 1
        fi

        log_git_operation "Lock acquired for: git $operation_desc"

        # Run the git command with appropriate output handling
        if [ "$verbose" = "true" ]; then
            # Verbose mode: show all output
            git "${git_cmd[@]}"
            local exit_code=$?
        else
            # Normal mode: capture output, show only on error
            local git_output
            git_output=$(git "${git_cmd[@]}" 2>&1)
            local exit_code=$?

            # Display error output if command failed
            if [ $exit_code -ne 0 ]; then
                echo "$git_output" >&2
            fi
        fi

        log_git_operation "Lock released for: git $operation_desc (exit: $exit_code)"

        return $exit_code
    ) 200>"$GIT_OPERATION_LOCK"

    local result=$?
    return $result
}

# Stash uncommitted changes
# Usage: stash_changes
# Returns 0 if changes were stashed, 1 if no changes, >1 on error
stash_changes() {
    wait_for_git_lock || return 1

    # diff-index returns: 0 = no changes, 1 = changes, >1 = error
    safe_git diff-index --quiet HEAD --
    local diff_status=$?
    if [ $diff_status -eq 1 ]; then
        print_warning "Uncommitted changes detected, stashing..."
        safe_git stash push -m "Auto-stash before /tree closedone at $(date +%Y%m%d-%H%M%S)"
        print_success "Changes stashed"
        return 0
    elif [ $diff_status -gt 1 ]; then
        return $diff_status
    fi
    return 1
}

# Check for stale git locks and cleanup if safe
# Usage: check_git_locks
check_git_locks() {
    local locks_found=false
    local locks_removed=false

    # Check for index.lock
    local index_lock="$WORKSPACE_ROOT/.git/index.lock"
    if [ -f "$index_lock" ]; then
        print_warning "Found git index.lock"

        if is_lock_stale "$index_lock"; then
            rm -f "$index_lock" 2>/dev/null && {
                print_success "Removed stale index.lock"
                locks_removed=true
            } || {
                print_error "Failed to remove index.lock (check permissions)"
                return 1
            }
        else
            print_error "Git operation in progress (index.lock is active)"
            print_info "Wait for operation to complete or remove manually: rm $index_lock"
            return 1
        fi
    fi

    # Check for worktree locks in .git/worktrees/*/locked
    if [ -d "$WORKSPACE_ROOT/.git/worktrees" ]; then
        for lock in "$WORKSPACE_ROOT/.git/worktrees"/*/locked; do
            if [ -f "$lock" ]; then
                # Get worktree name from lock file path (handle paths with spaces)
                local lock_dir
                lock_dir=$(dirname "$lock")
                local wt_name
                wt_name=$(basename "$lock_dir")
                print_warning "Found locked worktree: $wt_name"
                locks_found=true
            fi
        done
    fi

    if [ "$locks_found" = true ]; then
        print_warning "Locked worktrees detected - run 'git worktree prune' to clean up"
    fi

    if [ "$locks_removed" = false ] && [ "$locks_found" = false ]; then
        print_success "No stale locks detected"
    fi

    return 0
}
