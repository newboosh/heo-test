#!/bin/bash
#
# Script: commands/conflict.sh
# Purpose: Conflict detection commands for worktree system
# Created: 2026-01-28
# Description: Analyze feature conflicts across worktrees

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR, STAGED_FEATURES_FILE

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
