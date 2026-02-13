#!/bin/bash
#
# Script: commands/stage.sh
# Purpose: Feature staging commands for worktree system
# Created: 2026-01-28
# Description: Stage, list, and clear features for worktree creation

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR, STAGED_FEATURES_FILE

# /tree stage [description]
# Stage a feature for worktree creation
tree_stage() {
    local description="$*"

    if [ -z "$description" ]; then
        print_error "Feature description required"
        echo "Usage: /tree stage [description]"
        echo "Example: /tree stage Add real-time collaboration features with WebSocket support"
        return 1
    fi

    # Create .trees directory if it doesn't exist
    mkdir -p "$TREES_DIR"

    # Create staging file if it doesn't exist
    if [ ! -f "$STAGED_FEATURES_FILE" ]; then
        cat > "$STAGED_FEATURES_FILE" << EOF
# Staged Features for Worktree Build
# Created: $(date +%Y-%m-%d)
#
# Format: worktree-name|||Full description of the feature
# The ||| delimiter preserves the complete description for task context
# One feature per line

EOF
    fi

    # Generate worktree name from description (slugified)
    local worktree_name
    worktree_name=$(echo "$description" | \
        tr '[:upper:]' '[:lower:]' | \
        sed 's/[^a-z0-9 -]//g' | \
        sed 's/ \+/-/g' | \
        cut -c1-50 | \
        sed 's/-$//')

    # Validate slugified name is not empty or just dashes
    if [ -z "$worktree_name" ] || [[ "$worktree_name" =~ ^-+$ ]]; then
        print_error "Could not generate valid worktree name from description"
        echo "Please use a description with alphanumeric characters"
        return 1
    fi

    # Check if worktree name already exists
    if grep -q "^${worktree_name}|||" "$STAGED_FEATURES_FILE" 2>/dev/null; then
        print_warning "Feature with similar name already staged: $worktree_name"
        echo "Use a more specific description or remove the existing feature first"
        return 1
    fi

    # Append to staging file with ||| delimiter to preserve full description
    echo "${worktree_name}|||${description}" >> "$STAGED_FEATURES_FILE"

    # Count features
    local feature_count=$(grep -vc '^#\|^$' "$STAGED_FEATURES_FILE" || true)

    print_success "Feature $feature_count staged: $worktree_name"
    echo "        Objective: $description"
    echo ""
    echo "Options:"
    echo "  - Stage another feature: /tree stage [description]"
    echo "  - Review all staged: /tree list"
    echo "  - Build worktrees: /tree build"
}

# /tree list
# List all staged features
tree_list() {
    if [ ! -f "$STAGED_FEATURES_FILE" ]; then
        print_warning "No features staged yet"
        echo "Use: /tree stage [description] to stage your first feature"
        return 0
    fi

    # Read staged features (using ||| delimiter)
    # Note: IFS='|||' splits on single '|' chars, so we parse the full line instead
    local features=()
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [ -z "$line" ] && continue
        # Parse by ||| delimiter
        local name="${line%%|||*}"
        local desc="${line#*|||}"
        [ -z "$name" ] && continue
        features+=("$name|||$desc")
    done < "$STAGED_FEATURES_FILE"

    if [ ${#features[@]} -eq 0 ]; then
        print_warning "No features staged yet"
        echo "Use: /tree stage [description] to stage your first feature"
        return 0
    fi

    print_header "Staged Features (${#features[@]})"

    for i in "${!features[@]}"; do
        local feature="${features[$i]}"
        local name="${feature%%|||*}"
        local desc="${feature#*|||}"
        local num=$((i + 1))

        echo "$num. $name"
        echo "   $desc"
        echo ""
    done

    echo "Actions:"
    echo "  - /tree stage [description] - Add another"
    echo "  - /tree clear - Clear all staged features"
    echo "  - /tree build - Create all worktrees"
}

# /tree clear
# Clear all staged features
tree_clear() {
    if [ ! -f "$STAGED_FEATURES_FILE" ]; then
        print_info "No staged features to clear"
        return 0
    fi

    # Count features
    local feature_count=$(grep -vc '^#\|^$' "$STAGED_FEATURES_FILE" || true)

    if [ "$feature_count" -eq 0 ]; then
        print_info "No staged features to clear"
        return 0
    fi

    if confirm_prompt "Clear $feature_count staged feature(s)?" "n"; then
        rm -f "$STAGED_FEATURES_FILE"
        print_success "Cleared $feature_count staged feature(s)"
    else
        print_info "Clear cancelled"
    fi
}
