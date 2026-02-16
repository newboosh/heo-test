#!/bin/bash

# Git Queue Client Library
# Simple interface for submitting git operations to the queue

set -e

# Script's own directory (for finding sibling scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project workspace root
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo "/workspace")}"

# Queue manager is in the same directory as this script
QUEUE_MANAGER="$SCRIPT_DIR/git-queue-manager.sh"

# Source priority constants
PRIORITY_USER=10
PRIORITY_ORCHESTRATOR=8
PRIORITY_BACKGROUND=5
PRIORITY_METRICS=3
PRIORITY_CLEANUP=1

# ==============================================================================
# Client Functions
# ==============================================================================

# Submit a git operation to the queue with high priority (user-initiated)
#
# Usage:
#   queued_git commit -m "My commit"
#   queued_git push origin main
queued_git() {
    local operation="$*"

    # Ensure queue manager is running
    if ! bash "$QUEUE_MANAGER" status | grep -q "Running"; then
        echo "Starting queue manager..." >&2
        bash "$QUEUE_MANAGER" start >&2
        sleep 1
    fi

    # Enqueue with user priority
    local request_id=$(bash "$QUEUE_MANAGER" enqueue "$PRIORITY_USER" "$operation")

    if [ -n "$request_id" ]; then
        # Wait for completion
        bash "$QUEUE_MANAGER" wait "$request_id"
        return $?
    else
        echo "Error: Failed to enqueue operation" >&2
        return 1
    fi
}

# Submit a background git operation (lower priority)
queued_git_background() {
    local operation="$*"

    bash "$QUEUE_MANAGER" enqueue "$PRIORITY_BACKGROUND" "$operation" &
}

# Submit orchestrator operation (medium-high priority)
queued_git_orchestrator() {
    local operation="$*"

    local request_id=$(bash "$QUEUE_MANAGER" enqueue "$PRIORITY_ORCHESTRATOR" "$operation")

    if [ -n "$request_id" ]; then
        bash "$QUEUE_MANAGER" wait "$request_id" 120  # 2min timeout
        return $?
    else
        return 1
    fi
}

# Export functions
export -f queued_git
export -f queued_git_background
export -f queued_git_orchestrator
