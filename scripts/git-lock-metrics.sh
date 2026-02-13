#!/bin/bash

# Git Lock Metrics Collection System
# Collects and analyzes lock performance metrics for monitoring and optimization

set -e

# ==============================================================================
# Configuration
# ==============================================================================

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
METRICS_FILE="$WORKSPACE_ROOT/.git/.lock-metrics.csv"
METRICS_SUMMARY="$WORKSPACE_ROOT/.git/.lock-metrics-summary.json"
OPERATION_LOG="$WORKSPACE_ROOT/.git/.git-operations.log"

# Metrics retention (days)
RETENTION_DAYS=7

# ==============================================================================
# Initialization
# ==============================================================================

init_metrics() {
    # Create metrics file with header if it doesn't exist
    if [ ! -f "$METRICS_FILE" ]; then
        echo "timestamp,event_type,lock_scope,lock_file,duration_ms,operation,pid" > "$METRICS_FILE"
    fi
}

# ==============================================================================
# Metrics Collection
# ==============================================================================

# Record a lock metric event
#
# Args:
#   $1 - Event type (acquire|release|wait|timeout|stale)
#   $2 - Lock scope (global|worktree)
#   $3 - Lock file path
#   $4 - Duration in milliseconds
#   $5 - Operation description
record_metric() {
    local event_type="$1"
    local lock_scope="$2"
    local lock_file="$3"
    local duration_ms="$4"
    local operation="$5"
    local pid="$$"
    local timestamp=$(date +%s%3N)  # Milliseconds since epoch

    # Sanitize operation for CSV
    operation=$(echo "$operation" | tr ',' ';')

    echo "$timestamp,$event_type,$lock_scope,$lock_file,$duration_ms,$operation,$pid" >> "$METRICS_FILE"
}

# Record lock acquisition with timing
#
# Usage:
#   start_time=$(get_timestamp_ms)
#   # ... acquire lock ...
#   record_lock_acquisition "global" "$lock_file" "$start_time" "git merge"
record_lock_acquisition() {
    local scope="$1"
    local lock_file="$2"
    local start_time_ms="$3"
    local operation="$4"

    local end_time_ms=$(date +%s%3N)
    local duration=$((end_time_ms - start_time_ms))

    record_metric "acquire" "$scope" "$lock_file" "$duration" "$operation"
}

# Record lock wait time
record_lock_wait() {
    local scope="$1"
    local lock_file="$2"
    local wait_time_ms="$3"
    local operation="$4"

    record_metric "wait" "$scope" "$lock_file" "$wait_time_ms" "$operation"
}

# Record lock timeout
record_lock_timeout() {
    local scope="$1"
    local lock_file="$2"
    local operation="$3"

    record_metric "timeout" "$scope" "$lock_file" "0" "$operation"
}

# Record stale lock removal
record_stale_lock() {
    local lock_file="$1"
    local age_seconds="$2"

    record_metric "stale" "unknown" "$lock_file" "$((age_seconds * 1000))" "stale_removal"
}

# Get current timestamp in milliseconds
get_timestamp_ms() {
    date +%s%3N
}

# ==============================================================================
# Metrics Analysis
# ==============================================================================

# Calculate percentile from sorted data
#
# Args:
#   $1 - Percentile (50, 95, 99)
#   stdin - Sorted numeric values (one per line)
calculate_percentile() {
    local percentile=$1
    local count=$(wc -l)
    local index=$(awk "BEGIN {print int($count * $percentile / 100)}")

    sed -n "${index}p"
}

# Analyze lock metrics and generate summary
analyze_metrics() {
    if [ ! -f "$METRICS_FILE" ]; then
        echo '{"error": "No metrics file found"}' > "$METRICS_SUMMARY"
        return 1
    fi

    # Skip header and get last 24 hours of data
    local cutoff_time=$(($(date +%s) - 86400))000  # 24h in ms

    local temp_file=$(mktemp)

    # Filter recent data (last 24h)
    awk -F',' -v cutoff="$cutoff_time" 'NR > 1 && $1 >= cutoff' "$METRICS_FILE" > "$temp_file"

    # Calculate statistics
    local total_ops=$(wc -l < "$temp_file")

    if [ "$total_ops" -eq 0 ]; then
        echo '{"error": "No recent metrics", "period": "24h"}' > "$METRICS_SUMMARY"
        rm "$temp_file"
        return 0
    fi

    # Extract durations for acquisition events
    local durations=$(awk -F',' '$2 == "acquire" {print $5}' "$temp_file" | sort -n)

    local p50=$(echo "$durations" | calculate_percentile 50)
    local p95=$(echo "$durations" | calculate_percentile 95)
    local p99=$(echo "$durations" | calculate_percentile 99)
    local max=$(echo "$durations" | tail -1)
    local avg=$(echo "$durations" | awk '{sum+=$1} END {if (NR>0) print int(sum/NR); else print 0}')

    # Count events by type
    local acquire_count=$(awk -F',' '$2 == "acquire"' "$temp_file" | wc -l)
    local wait_count=$(awk -F',' '$2 == "wait"' "$temp_file" | wc -l)
    local timeout_count=$(awk -F',' '$2 == "timeout"' "$temp_file" | wc -l)
    local stale_count=$(awk -F',' '$2 == "stale"' "$temp_file" | wc -l)

    # Count by scope
    local global_count=$(awk -F',' '$3 == "global"' "$temp_file" | wc -l)
    local worktree_count=$(awk -F',' '$3 == "worktree"' "$temp_file" | wc -l)

    # Top operations by frequency
    local top_ops=$(awk -F',' 'NR > 1 {print $6}' "$temp_file" | sort | uniq -c | sort -rn | head -5 | \
        awk '{printf "{\"operation\":\"%s\",\"count\":%d}", substr($0, index($0,$2)), $1}' | \
        paste -sd ',' -)

    # Generate JSON summary
    cat > "$METRICS_SUMMARY" <<EOF
{
    "period": "24h",
    "timestamp": "$(date -Iseconds)",
    "total_operations": $total_ops,
    "acquisition_stats": {
        "count": $acquire_count,
        "avg_ms": ${avg:-0},
        "p50_ms": ${p50:-0},
        "p95_ms": ${p95:-0},
        "p99_ms": ${p99:-0},
        "max_ms": ${max:-0}
    },
    "events": {
        "acquires": $acquire_count,
        "waits": $wait_count,
        "timeouts": $timeout_count,
        "stale_removals": $stale_count
    },
    "scope_distribution": {
        "global": $global_count,
        "worktree": $worktree_count
    },
    "top_operations": [$top_ops]
}
EOF

    rm "$temp_file"
}

# ==============================================================================
# Metrics Cleanup
# ==============================================================================

# Clean old metrics beyond retention period
cleanup_old_metrics() {
    if [ ! -f "$METRICS_FILE" ]; then
        return 0
    fi

    local cutoff_time=$(($(date +%s) - (RETENTION_DAYS * 86400)))000  # Days in ms

    local temp_file=$(mktemp)

    # Keep header + recent data
    head -1 "$METRICS_FILE" > "$temp_file"
    awk -F',' -v cutoff="$cutoff_time" 'NR > 1 && $1 >= cutoff' "$METRICS_FILE" >> "$temp_file"

    mv "$temp_file" "$METRICS_FILE"

    echo "Cleaned metrics older than $RETENTION_DAYS days"
}

# ==============================================================================
# Real-time Monitoring
# ==============================================================================

# Show recent lock activity (last N events)
show_recent_activity() {
    local count=${1:-20}

    if [ ! -f "$METRICS_FILE" ]; then
        echo "No metrics available"
        return 1
    fi

    echo "=== Recent Lock Activity (last $count events) ==="
    echo ""

    # Format and display
    tail -n "$count" "$METRICS_FILE" | \
        awk -F',' 'NR > 1 {
            # Convert timestamp to human-readable
            timestamp = strftime("%Y-%m-%d %H:%M:%S", $1/1000);
            printf "%s | %-8s | %-8s | %4dms | %s\n", timestamp, $2, $3, $5, $6;
        }'
}

# Show lock contention hotspots
show_hotspots() {
    if [ ! -f "$METRICS_FILE" ]; then
        echo "No metrics available"
        return 1
    fi

    echo "=== Lock Contention Hotspots ==="
    echo ""

    local cutoff_time=$(($(date +%s) - 3600))000  # Last hour

    # Find operations with high wait times
    awk -F',' -v cutoff="$cutoff_time" '
        NR > 1 && $1 >= cutoff && $2 == "acquire" && $5 > 1000 {
            print $5 " ms - " $6
        }
    ' "$METRICS_FILE" | sort -rn | head -10

    echo ""
    echo "=== Most Contended Locks (last hour) ==="
    awk -F',' -v cutoff="$cutoff_time" '
        NR > 1 && $1 >= cutoff && $2 == "wait" {
            lock = $4;
            sub(/.*\//, "", lock);  # Get basename
            count[lock]++;
        }
        END {
            for (lock in count) {
                printf "%3d waits - %s\n", count[lock], lock;
            }
        }
    ' "$METRICS_FILE" | sort -rn | head -10
}

# Generate metrics report
generate_report() {
    analyze_metrics

    echo "=== Git Lock Metrics Report ==="
    echo ""
    echo "Generated: $(date)"
    echo ""

    if [ -f "$METRICS_SUMMARY" ]; then
        # Parse and display JSON summary
        cat "$METRICS_SUMMARY" | python3 -c "
import json, sys
data = json.load(sys.stdin)

if 'error' in data:
    print(f\"Error: {data['error']}\")
    sys.exit(0)

print(f\"Period: {data['period']}\")
print(f\"Total Operations: {data['total_operations']}\")
print()
print('Acquisition Statistics:')
stats = data['acquisition_stats']
print(f\"  Count: {stats['count']}\")
print(f\"  Average: {stats['avg_ms']}ms\")
print(f\"  P50: {stats['p50_ms']}ms\")
print(f\"  P95: {stats['p95_ms']}ms\")
print(f\"  P99: {stats['p99_ms']}ms\")
print(f\"  Max: {stats['max_ms']}ms\")
print()
print('Event Distribution:')
events = data['events']
print(f\"  Acquisitions: {events['acquires']}\")
print(f\"  Waits: {events['waits']}\")
print(f\"  Timeouts: {events['timeouts']}\")
print(f\"  Stale Removals: {events['stale_removals']}\")
print()
print('Scope Distribution:')
scope = data['scope_distribution']
print(f\"  Global: {scope['global']}\")
print(f\"  Worktree: {scope['worktree']}\")
print()
print('Top Operations:')
for i, op in enumerate(data['top_operations'], 1):
    print(f\"  {i}. {op['operation']} ({op['count']} times)\")
" 2>/dev/null || cat "$METRICS_SUMMARY"
    else
        echo "No summary available"
    fi
}

# ==============================================================================
# CLI Interface
# ==============================================================================

case "${1:-}" in
    init)
        init_metrics
        echo "Metrics system initialized"
        ;;
    analyze)
        analyze_metrics
        echo "Metrics analyzed, summary written to: $METRICS_SUMMARY"
        ;;
    report)
        generate_report
        ;;
    recent)
        show_recent_activity "${2:-20}"
        ;;
    hotspots)
        show_hotspots
        ;;
    cleanup)
        cleanup_old_metrics
        ;;
    *)
        echo "Usage: $0 {init|analyze|report|recent [count]|hotspots|cleanup}"
        echo ""
        echo "Commands:"
        echo "  init     - Initialize metrics system"
        echo "  analyze  - Analyze metrics and generate summary"
        echo "  report   - Generate human-readable report"
        echo "  recent   - Show recent lock activity"
        echo "  hotspots - Show lock contention hotspots"
        echo "  cleanup  - Remove old metrics"
        exit 1
        ;;
esac

# Initialize on first run
init_metrics

# Export functions
export -f record_metric
export -f record_lock_acquisition
export -f record_lock_wait
export -f record_lock_timeout
export -f record_stale_lock
export -f get_timestamp_ms
