#!/bin/bash
#
# Script: commands/conflict.sh
# Purpose: Conflict detection commands for worktree system
# Created: 2026-01-28
# Description: Analyze scope and feature conflicts across worktrees

# Dependencies: lib/common.sh (print_* functions), scope-detector.sh
# Required variables: TREES_DIR, STAGED_FEATURES_FILE

# /tree scope-conflicts
# Detect scope conflicts across all active worktrees
tree_scope_conflicts() {
    print_header "Scope Conflict Detection"

    local scope_files=()
    local worktree_count=0

    # Find all worktrees with scope files
    for worktree_dir in "$TREES_DIR"/*; do
        if [ -d "$worktree_dir" ] && [[ "$(basename "$worktree_dir")" != ".conflict-backup" ]]; then
            local scope_file="$worktree_dir/.worktree-scope.json"
            if [ -f "$scope_file" ]; then
                scope_files+=("$scope_file")
                worktree_count=$((worktree_count + 1))
            fi
        fi
    done

    if [ $worktree_count -eq 0 ]; then
        print_info "No active worktrees with scope files found"
        return 0
    fi

    echo "Analyzing scope conflicts across $worktree_count worktree(s)..."
    echo ""

    # Call scope detection utility if available
    if type detect_scope_conflicts &>/dev/null; then
        if detect_scope_conflicts "${scope_files[@]}"; then
            print_success "No scope conflicts detected"
            echo ""
            print_info "All worktrees have non-overlapping scopes"
        else
            print_warning "Scope conflicts detected - see above for details"
            echo ""
            print_info "Resolution options:"
            echo "  1. Adjust scope patterns in .worktree-scope.json files"
            echo "  2. Merge related worktrees"
            echo "  3. Use enforcement: 'hard' to block conflicting commits"
            return 1
        fi
    else
        print_warning "Scope detection function not available"
        print_info "Ensure scope-detector.sh is sourced correctly"
        return 1
    fi
}

# /tree conflict
# Analyze conflicts between staged features
tree_conflict() {
    if [ ! -f "$STAGED_FEATURES_FILE" ]; then
        print_error "No features staged"
        echo "Use: /tree stage [description] to stage features first"
        return 1
    fi

    print_header "Conflict Analysis"

    # Read staged features (using ||| delimiter)
    # Note: IFS='|||' splits on single '|' chars, so parse the full line instead
    local features=()
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [ -z "$line" ] && continue
        local name="${line%%|||*}"
        [ -z "$name" ] && continue
        features+=("$line")
    done < "$STAGED_FEATURES_FILE"

    if [ ${#features[@]} -eq 0 ]; then
        print_error "No features to analyze"
        return 1
    fi

    echo "Analyzing ${#features[@]} staged features..."
    echo ""

    # Simple keyword-based conflict detection
    print_info "MERGE SUGGESTIONS:"
    echo ""

    local suggestions_found=false

    # Check for similar feature names
    for i in "${!features[@]}"; do
        local feature_i="${features[$i]}"
        local name_i="${feature_i%%|||*}"
        local desc_i="${feature_i#*|||}"

        for j in "${!features[@]}"; do
            [ $i -ge $j ] && continue

            local feature_j="${features[$j]}"
            local name_j="${feature_j%%|||*}"
            local desc_j="${feature_j#*|||}"

            # Check for keyword overlaps (separate declaration from assignment)
            local common_words
            common_words=$(comm -12 \
                <(echo "$desc_i" | tr ' ' '\n' | sort -u) \
                <(echo "$desc_j" | tr ' ' '\n' | sort -u) | wc -l)

            if [ $common_words -gt 3 ]; then
                suggestions_found=true
                echo "+-------------------------------------------------------------+"
                echo "| Features $((i+1)) & $((j+1)) may be related - consider merging?"
                echo "|"
                echo "| Feature $((i+1)): ${name_i:0:50}"
                echo "| Feature $((j+1)): ${name_j:0:50}"
                echo "|"
                echo "| Common keywords detected: $common_words"
                echo "+-------------------------------------------------------------+"
                echo ""
            fi
        done
    done

    if [ "$suggestions_found" = false ]; then
        print_success "No obvious overlaps detected"
        echo ""
    fi

    echo "CONFLICT ANALYSIS:"
    echo ""
    print_success "Analysis complete"
    print_info "For detailed conflict analysis, review feature descriptions above"
    echo ""
    echo "Actions:"
    echo "  - /tree stage [description] - Add more features"
    echo "  - /tree list - Review all staged"
    echo "  - /tree build - Create worktrees"
}
