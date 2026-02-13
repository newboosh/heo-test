#!/bin/bash

# Git Lock Predictor - Pattern Learning and Predictive Lock Management
# Analyzes operation sequences and pre-acquires locks for anticipated operations

set -e

# ==============================================================================
# Configuration
# ==============================================================================

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
PATTERN_DB="$WORKSPACE_ROOT/.git/.lock-patterns.db"
OPERATION_LOG="$WORKSPACE_ROOT/.git/.git-operations.log"
PREDICTOR_STATE="$WORKSPACE_ROOT/.git/.predictor-state.json"

# Prediction settings
MIN_CONFIDENCE=0.70  # 70% confidence threshold
LEARNING_WINDOW=100  # Look at last N operations
PREDICTION_LOOKAHEAD=3  # Predict next N operations

# ==============================================================================
# Pattern Database
# ==============================================================================

# Initialize pattern database
init_pattern_db() {
    if [ ! -f "$PATTERN_DB" ]; then
        # Format: operation|next_operation|count
        echo "# Pattern database for predictive lock management" > "$PATTERN_DB"
        echo "# Format: current_op | next_op | count" >> "$PATTERN_DB"
    fi
}

# Record an operation sequence for learning
#
# Args:
#   $1 - Current operation
#   $2 - Next operation
record_sequence() {
    local current_op="$1"
    local next_op="$2"

    # Sanitize operations
    current_op=$(echo "$current_op" | tr ' ' '_' | tr -d '|')
    next_op=$(echo "$next_op" | tr ' ' '_' | tr -d '|')

    local pattern="$current_op|$next_op"

    # Check if pattern exists
    if grep -q "^$pattern|" "$PATTERN_DB" 2>/dev/null; then
        # Increment count
        local current_count=$(grep "^$pattern|" "$PATTERN_DB" | cut -d'|' -f3)
        local new_count=$((current_count + 1))

        # Update count
        sed -i.bak "s/^$pattern|[0-9]*$/$pattern|$new_count/" "$PATTERN_DB"
        rm -f "$PATTERN_DB.bak"
    else
        # Add new pattern
        echo "$pattern|1" >> "$PATTERN_DB"
    fi
}

# Learn patterns from operation log
learn_from_log() {
    if [ ! -f "$OPERATION_LOG" ]; then
        return 0
    fi

    # Get last N operations
    local recent_ops=$(tail -n "$LEARNING_WINDOW" "$OPERATION_LOG" | \
        grep "operation_complete" | \
        sed 's/.*op=git \([^ ]*\).*/\1/' | \
        grep -v "^$")

    # Build sequences
    local prev_op=""
    while IFS= read -r op; do
        if [ -n "$prev_op" ]; then
            record_sequence "$prev_op" "$op"
        fi
        prev_op="$op"
    done <<< "$recent_ops"

    # Clean up patterns with very low frequency (< 2 occurrences)
    grep -v "^#" "$PATTERN_DB" | awk -F'|' '$3 >= 2' > "$PATTERN_DB.tmp"
    grep "^#" "$PATTERN_DB" > "$PATTERN_DB.new"
    cat "$PATTERN_DB.tmp" >> "$PATTERN_DB.new"
    mv "$PATTERN_DB.new" "$PATTERN_DB"
    rm -f "$PATTERN_DB.tmp"
}

# ==============================================================================
# Prediction Engine
# ==============================================================================

# Predict next likely operations given current operation
#
# Args:
#   $1 - Current operation
# Returns:
#   List of predicted operations with confidence scores
predict_next_operations() {
    local current_op="$1"
    current_op=$(echo "$current_op" | tr ' ' '_' | tr -d '|')

    if [ ! -f "$PATTERN_DB" ]; then
        return 0
    fi

    # Find all patterns starting with current operation
    local patterns=$(grep "^$current_op|" "$PATTERN_DB" 2>/dev/null || true)

    if [ -z "$patterns" ]; then
        return 0
    fi

    # Calculate total occurrences
    local total=$(echo "$patterns" | awk -F'|' '{sum += $3} END {print sum}')

    if [ "$total" -eq 0 ]; then
        return 0
    fi

    # Calculate confidence for each next operation
    echo "$patterns" | while IFS='|' read -r curr next count; do
        local confidence=$(awk "BEGIN {printf \"%.2f\", $count / $total}")

        # Only return predictions above confidence threshold
        if (( $(awk "BEGIN {print ($confidence >= $MIN_CONFIDENCE)}") )); then
            echo "$next:$confidence"
        fi
    done | sort -t':' -k2 -rn | head -n "$PREDICTION_LOOKAHEAD"
}

# Get lock scope for an operation
get_lock_scope_for_op() {
    local operation="$1"

    case "$operation" in
        merge|rebase|pull|fetch|push|worktree|branch)
            echo "global"
            ;;
        add|commit|status|diff|stash|reset)
            echo "worktree"
            ;;
        *)
            echo "global"  # Default to global for safety
            ;;
    esac
}

# ==============================================================================
# Pre-Acquisition
# ==============================================================================

# Pre-acquire locks for predicted operations (non-blocking)
#
# Args:
#   $1 - Current operation
preacquire_locks() {
    local current_op="$1"

    # Get predictions
    local predictions=$(predict_next_operations "$current_op")

    if [ -z "$predictions" ]; then
        return 0
    fi

    # Log predictions
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Predictions for '$current_op':" >> "$PREDICTOR_STATE"

    while IFS=':' read -r next_op confidence; do
        local scope=$(get_lock_scope_for_op "$next_op")

        echo "[$(date '+%Y-%m-%d %H:%M:%S')]   → $next_op (confidence: $confidence, scope: $scope)" >> "$PREDICTOR_STATE"

        # In practice, this would trigger async lock pre-acquisition
        # For now, we just log the intent
        # Future: Implement background worker to actually acquire locks
    done <<< "$predictions"
}

# ==============================================================================
# Workflow Integration
# ==============================================================================

# Hook into operation start - predict and pre-acquire
on_operation_start() {
    local operation="$1"

    # Predict next operations
    preacquire_locks "$operation"
}

# Hook into operation complete - learn pattern
on_operation_complete() {
    local operation="$1"

    # Pattern learning happens in batch via learn_from_log
    # This hook is for future real-time learning
    :
}

# ==============================================================================
# Pattern Analysis & Reporting
# ==============================================================================

# Show learned patterns
show_patterns() {
    if [ ! -f "$PATTERN_DB" ]; then
        echo "No patterns learned yet"
        return 1
    fi

    echo "=== Learned Operation Patterns ==="
    echo ""
    echo "Format: Current Operation → Next Operation (Count)"
    echo ""

    # Sort by count descending
    grep -v "^#" "$PATTERN_DB" | sort -t'|' -k3 -rn | while IFS='|' read -r curr next count; do
        # Calculate percentage of total
        curr_display=$(echo "$curr" | tr '_' ' ')
        next_display=$(echo "$next" | tr '_' ' ')

        printf "%-20s → %-20s (%3d occurrences)\n" "$curr_display" "$next_display" "$count"
    done
}

# Show prediction accuracy statistics
show_accuracy() {
    echo "=== Prediction Accuracy Analysis ==="
    echo ""

    if [ ! -f "$OPERATION_LOG" ]; then
        echo "No operation log available"
        return 1
    fi

    # Get recent operation pairs
    local recent_pairs=$(tail -n 50 "$OPERATION_LOG" | \
        grep "operation_complete" | \
        sed 's/.*op=git \([^ ]*\).*/\1/' | \
        awk 'NR>1 {print prev,$0} {prev=$0}')

    local total=0
    local correct=0

    while read -r curr next; do
        total=$((total + 1))

        # Get prediction for current
        local predicted=$(predict_next_operations "$curr" | head -1 | cut -d':' -f1)

        if [ "$predicted" = "$next" ]; then
            correct=$((correct + 1))
        fi
    done <<< "$recent_pairs"

    if [ "$total" -gt 0 ]; then
        local accuracy=$(awk "BEGIN {printf \"%.1f\", ($correct / $total) * 100}")
        echo "Recent Operations Analyzed: $total"
        echo "Correct Predictions: $correct"
        echo "Accuracy: ${accuracy}%"
        echo ""

        if (( $(awk "BEGIN {print ($accuracy >= 70)}") )); then
            echo "✓ Prediction system is performing well"
        else
            echo "⚠ Prediction accuracy below threshold (70%)"
            echo "  Recommend more training data"
        fi
    else
        echo "Not enough data to calculate accuracy"
    fi
}

# Show common workflows detected
show_workflows() {
    echo "=== Detected Workflows ==="
    echo ""

    if [ ! -f "$PATTERN_DB" ]; then
        echo "No workflows detected yet"
        return 1
    fi

    # Common workflow patterns
    declare -A workflows=(
        ["worktree_add"]="worktree add → checkout → status"
        ["commit_flow"]="add → commit → push"
        ["merge_flow"]="checkout → merge → push"
        ["tree_build"]="checkout → worktree → worktree → status"
    )

    for workflow_name in "${!workflows[@]}"; do
        local workflow="${workflows[$workflow_name]}"
        echo "$workflow_name:"
        echo "  $workflow"

        # Check if this pattern exists
        # Simplified check - just look for first pair
        local first_op=$(echo "$workflow" | cut -d'→' -f1 | tr -d ' ')
        local pattern_count=$(grep -c "^$first_op|" "$PATTERN_DB" 2>/dev/null || echo "0")

        if [ "$pattern_count" -gt 0 ]; then
            echo "  ✓ Pattern detected ($pattern_count occurrences)"
        else
            echo "  ✗ Pattern not yet learned"
        fi
        echo ""
    done
}

# ==============================================================================
# Maintenance
# ==============================================================================

# Reset all learned patterns
reset_patterns() {
    rm -f "$PATTERN_DB"
    rm -f "$PREDICTOR_STATE"
    init_pattern_db
    echo "Pattern database reset"
}

# ==============================================================================
# CLI Interface
# ==============================================================================

case "${1:-}" in
    init)
        init_pattern_db
        echo "Predictor initialized"
        ;;
    learn)
        learn_from_log
        echo "Learned patterns from operation log"
        ;;
    predict)
        if [ -z "$2" ]; then
            echo "Usage: $0 predict <operation>"
            exit 1
        fi
        predict_next_operations "$2"
        ;;
    patterns)
        show_patterns
        ;;
    accuracy)
        show_accuracy
        ;;
    workflows)
        show_workflows
        ;;
    reset)
        reset_patterns
        ;;
    *)
        echo "Usage: $0 {init|learn|predict|patterns|accuracy|workflows|reset}"
        echo ""
        echo "Commands:"
        echo "  init       - Initialize predictor"
        echo "  learn      - Learn patterns from operation log"
        echo "  predict    - Predict next operations for given operation"
        echo "  patterns   - Show learned patterns"
        echo "  accuracy   - Show prediction accuracy statistics"
        echo "  workflows  - Show detected workflows"
        echo "  reset      - Reset all learned patterns"
        exit 1
        ;;
esac

# Initialize on first run
init_pattern_db

# Export functions
export -f predict_next_operations
export -f preacquire_locks
export -f on_operation_start
export -f on_operation_complete
