#!/bin/bash

# Git Queue Manager - Centralized Queue System for Git Operations
# Provides fair scheduling and eliminates race conditions

set -e

# ==============================================================================
# Configuration
# ==============================================================================

# Script's own directory (for finding sibling scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project workspace root (for git operations)
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || echo "/workspace")}"
QUEUE_DIR="$WORKSPACE_ROOT/.git/.git-lock-queue"
QUEUE_FILE="$QUEUE_DIR/queue.fifo"
MANAGER_PID_FILE="$QUEUE_DIR/manager.pid"
STATUS_FILE="$QUEUE_DIR/status.json"
RESULT_DIR="$QUEUE_DIR/results"

# Priority levels
PRIORITY_USER=10
PRIORITY_ORCHESTRATOR=8
PRIORITY_BACKGROUND=5
PRIORITY_METRICS=3
PRIORITY_CLEANUP=1

# ==============================================================================
# Initialization
# ==============================================================================

init_queue() {
    mkdir -p "$QUEUE_DIR"
    mkdir -p "$RESULT_DIR"

    # Create FIFO if it doesn't exist
    if [ ! -p "$QUEUE_FILE" ]; then
        mkfifo "$QUEUE_FILE"
    fi

    # Initialize status
    cat > "$STATUS_FILE" <<EOF
{
    "state": "stopped",
    "manager_pid": null,
    "queued_operations": 0,
    "completed_operations": 0,
    "failed_operations": 0,
    "started_at": null
}
EOF
}

# ==============================================================================
# Queue Manager (Worker Process)
# ==============================================================================

# Main queue worker loop
queue_worker() {
    echo "Queue manager starting (PID: $$)"

    # Update status
    update_status "running" "$$" 0 0 0

    # Trap signals for graceful shutdown
    trap 'cleanup_worker' TERM INT

    local completed=0
    local failed=0

    # Main processing loop
    while true; do
        # Read next operation from queue (blocking)
        if read -r queue_item < "$QUEUE_FILE"; then
            # Parse queue item: priority|operation|worktree|client_pid|request_id
            IFS='|' read -r priority operation worktree client_pid request_id <<< "$queue_item"

            echo "[$(date '+%H:%M:%S')] Processing: $operation (priority: $priority, pid: $client_pid)"

            # Execute operation
            local result_file="$RESULT_DIR/$request_id.result"
            local exit_code=0

            # Run operation with appropriate lock
            if execute_operation "$operation" "$worktree" > "$result_file" 2>&1; then
                echo "SUCCESS" > "$RESULT_DIR/$request_id.status"
                completed=$((completed + 1))
            else
                exit_code=$?
                echo "FAILED:$exit_code" > "$RESULT_DIR/$request_id.status"
                failed=$((failed + 1))
            fi

            # Update status
            update_status "running" "$$" 0 "$completed" "$failed"

            # Notify client if still running
            if kill -0 "$client_pid" 2>/dev/null; then
                kill -USR1 "$client_pid" 2>/dev/null || true
            fi
        fi
    done
}

# Execute a git operation
execute_operation() {
    local operation="$1"
    local worktree="$2"

    # Change to worktree directory if specified
    if [ -n "$worktree" ] && [ -d "$worktree" ]; then
        cd "$worktree"
    fi

    # Source lock manager for safe_git (from plugin's scripts directory)
    if [ -f "$SCRIPT_DIR/git-lock-manager.sh" ]; then
        source "$SCRIPT_DIR/git-lock-manager.sh"
        safe_git_advanced $operation
    else
        # Fallback: direct git
        git $operation
    fi
}

# Cleanup on worker shutdown
cleanup_worker() {
    echo "Queue manager shutting down gracefully"

    update_status "stopped" "null" 0 0 0

    rm -f "$MANAGER_PID_FILE"

    exit 0
}

# ==============================================================================
# Queue Client Interface
# ==============================================================================

# Enqueue a git operation
#
# Args:
#   $1 - Priority (1-10)
#   $2 - Git operation (e.g., "commit -m 'message'")
#   $3 - Worktree path (optional)
# Returns:
#   Request ID for tracking
enqueue_operation() {
    local priority="$1"
    local operation="$2"
    local worktree="${3:-}"
    local client_pid="$$"
    local request_id="req_$(date +%s%N)"

    # Ensure queue is initialized
    if [ ! -p "$QUEUE_FILE" ]; then
        echo "Error: Queue not initialized. Run: git-queue-manager.sh start" >&2
        return 1
    fi

    # Check if manager is running
    if ! is_manager_running; then
        echo "Error: Queue manager not running. Run: git-queue-manager.sh start" >&2
        return 1
    fi

    # Write to queue
    echo "$priority|$operation|$worktree|$client_pid|$request_id" > "$QUEUE_FILE" &

    # Return request ID
    echo "$request_id"
}

# Wait for operation to complete
#
# Args:
#   $1 - Request ID
#   $2 - Timeout in seconds (default: 60)
# Returns:
#   0 on success, 1 on failure/timeout
wait_for_completion() {
    local request_id="$1"
    local timeout="${2:-60}"
    local status_file="$RESULT_DIR/$request_id.status"
    local result_file="$RESULT_DIR/$request_id.result"

    local start_time=$SECONDS

    # Wait for status file (check every 0.1s until timeout seconds elapsed)
    while [ ! -f "$status_file" ] && [ $((SECONDS - start_time)) -lt $timeout ]; do
        sleep 0.1
    done

    if [ ! -f "$status_file" ]; then
        echo "Error: Operation timed out after ${timeout}s" >&2
        return 1
    fi

    # Read status
    local status=$(cat "$status_file")

    # Show result
    if [ -f "$result_file" ]; then
        cat "$result_file"
    fi

    # Cleanup
    rm -f "$status_file" "$result_file"

    # Return exit code
    if [[ "$status" == "SUCCESS" ]]; then
        return 0
    else
        return 1
    fi
}

# ==============================================================================
# Manager Control
# ==============================================================================

# Start queue manager
start_manager() {
    if is_manager_running; then
        echo "Queue manager already running (PID: $(cat "$MANAGER_PID_FILE"))"
        return 0
    fi

    echo "Starting queue manager..."

    init_queue

    # Start worker in background
    queue_worker &
    local worker_pid=$!

    # Save PID
    echo "$worker_pid" > "$MANAGER_PID_FILE"

    # Wait a moment to ensure it started
    sleep 0.5

    if is_manager_running; then
        echo "Queue manager started (PID: $worker_pid)"
        return 0
    else
        echo "Failed to start queue manager"
        return 1
    fi
}

# Stop queue manager
stop_manager() {
    if ! is_manager_running; then
        echo "Queue manager not running"
        return 0
    fi

    local pid=$(cat "$MANAGER_PID_FILE")

    echo "Stopping queue manager (PID: $pid)..."

    # Send TERM signal for graceful shutdown
    kill -TERM "$pid" 2>/dev/null || true

    # Wait for shutdown (max 5 seconds)
    local waited=0
    while is_manager_running && [ $waited -lt 50 ]; do
        sleep 0.1
        waited=$((waited + 1))
    done

    if is_manager_running; then
        # Force kill if still running
        kill -KILL "$pid" 2>/dev/null || true
        rm -f "$MANAGER_PID_FILE"
    fi

    echo "Queue manager stopped"
}

# Restart queue manager
restart_manager() {
    stop_manager
    sleep 1
    start_manager
}

# Check if manager is running
is_manager_running() {
    if [ ! -f "$MANAGER_PID_FILE" ]; then
        return 1
    fi

    local pid=$(cat "$MANAGER_PID_FILE")

    if kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        # Stale PID file
        rm -f "$MANAGER_PID_FILE"
        return 1
    fi
}

# ==============================================================================
# Status & Monitoring
# ==============================================================================

# Update status file
update_status() {
    local state="$1"
    local pid="$2"
    local queued="$3"
    local completed="$4"
    local failed="$5"

    cat > "$STATUS_FILE" <<EOF
{
    "state": "$state",
    "manager_pid": $pid,
    "queued_operations": $queued,
    "completed_operations": $completed,
    "failed_operations": $failed,
    "updated_at": "$(date -Iseconds)"
}
EOF
}

# Show queue status
show_status() {
    echo "=== Git Queue Manager Status ==="
    echo ""

    if is_manager_running; then
        local pid=$(cat "$MANAGER_PID_FILE")
        echo "State: ✓ Running (PID: $pid)"
    else
        echo "State: ✗ Stopped"
    fi

    echo ""

    if [ -f "$STATUS_FILE" ]; then
        # Parse and display JSON status
        cat "$STATUS_FILE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Queued Operations: {data['queued_operations']}\")
print(f\"Completed Operations: {data['completed_operations']}\")
print(f\"Failed Operations: {data['failed_operations']}\")
if 'updated_at' in data:
    print(f\"Last Updated: {data['updated_at']}\")
" 2>/dev/null || echo "Status file format error"
    else
        echo "No status information available"
    fi

    echo ""

    # Show pending results
    local pending=$(ls "$RESULT_DIR"/*.result 2>/dev/null | wc -l)
    echo "Pending Results: $pending"
}

# ==============================================================================
# CLI Interface
# ==============================================================================

case "${1:-}" in
    start)
        start_manager
        ;;
    stop)
        stop_manager
        ;;
    restart)
        restart_manager
        ;;
    status)
        show_status
        ;;
    enqueue)
        if [ -z "$2" ]; then
            echo "Usage: $0 enqueue <priority> <operation> [worktree]"
            exit 1
        fi
        enqueue_operation "$2" "$3" "${4:-}"
        ;;
    worker)
        # Internal command - start worker directly
        queue_worker
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|enqueue}"
        echo ""
        echo "Commands:"
        echo "  start     - Start queue manager"
        echo "  stop      - Stop queue manager"
        echo "  restart   - Restart queue manager"
        echo "  status    - Show queue status"
        echo "  enqueue   - Enqueue operation (priority operation [worktree])"
        echo ""
        echo "Example:"
        echo "  $0 start"
        echo "  $0 enqueue 10 'commit -m \"Initial commit\"'"
        exit 1
        ;;
esac
