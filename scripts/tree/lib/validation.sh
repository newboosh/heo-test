#!/bin/bash
#
# Script: lib/validation.sh
# Purpose: Worktree validation and cleanup functions
# Created: 2026-01-28
# Description: Validates worktree state and provides safe cleanup operations

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR

# Validate worktree has no uncommitted changes
# Returns 0 if clean, 1 if dirty
validate_worktree_clean() {
    local worktree=$1
    local worktree_path="$TREES_DIR/$worktree"

    # Check if worktree directory exists
    if [ ! -d "$worktree_path" ]; then
        return 0  # Directory doesn't exist, consider clean
    fi

    # Check for uncommitted changes
    if (cd "$worktree_path" && [ -n "$(git status --porcelain 2>/dev/null)" ]); then
        return 1  # Dirty
    fi

    return 0  # Clean
}

# Validate that a path is safe to cleanup (prevent accidental data loss)
validate_cleanup_safe() {
    local target_path=$1

    # Must be within .trees directory
    if [[ "$target_path" != "$TREES_DIR"/* ]]; then
        print_error "Refusing to cleanup path outside .trees/: $target_path"
        return 1
    fi

    # Must not be a special directory
    local basename
    basename=$(basename "$target_path")
    if [[ "$basename" == .conflict-backup ]]; then
        print_error "Refusing to cleanup special directory: $basename"
        return 1
    fi

    # Check for uncommitted changes if it's a git worktree
    if [ -d "$target_path" ] && ([ -f "$target_path/.git" ] || [ -d "$target_path/.git" ]); then
        if ! (cd "$target_path" && git diff-index --quiet HEAD -- 2>/dev/null); then
            print_warning "Path has uncommitted changes: $target_path"
            return 1
        fi
    fi

    return 0
}

# Validate and cleanup a worktree path before creation
# Returns 0 if path is ready, 1 if blocked
validate_and_cleanup_worktree_path() {
    local worktree_path=$1
    local branch=$2

    # Check if path exists
    if [ -e "$worktree_path" ]; then
        print_warning "  Path already exists: $worktree_path"

        # Check if it's a valid worktree registered with git
        # Use grep -Fx for exact fixed-string line matching to avoid prefix collisions
        if git worktree list --porcelain 2>/dev/null | grep -Fxq "worktree $worktree_path"; then
            print_error "  Worktree already registered at this path"
            print_info "  Run: git worktree remove $worktree_path"
            return 1
        fi

        # It's an orphaned/corrupted directory - validate cleanup is safe
        if ! validate_cleanup_safe "$worktree_path"; then
            print_error "  Cannot safely cleanup path (has uncommitted work or outside .trees/)"
            return 1
        fi

        # Safe to remove - it's an orphaned directory
        print_warning "  Removing orphaned directory..."
        rm -rf "$worktree_path"
        print_success "  Orphaned directory removed"
    fi

    # Check if branch already exists
    if git rev-parse --verify "$branch" &>/dev/null; then
        print_warning "  Branch already exists: $branch"

        # Check if it's orphaned (no worktree associated)
        # Use grep -Fx for exact fixed-string line matching to handle branch names with regex metacharacters
        if ! git worktree list --porcelain 2>/dev/null | grep -Fxq "branch refs/heads/$branch"; then
            print_warning "  Orphaned branch detected - deleting..."
            if git branch -D "$branch" &>/dev/null; then
                print_success "  Orphaned branch removed"
            else
                print_error "  Failed to remove orphaned branch"
                return 1
            fi
        else
            print_error "  Branch in use by another worktree"
            local worktree_using
            # Use awk with substr to handle paths containing spaces
            worktree_using=$(git worktree list --porcelain | awk -v b="refs/heads/$branch" '
                /^worktree /{path=substr($0, 10)}
                /^branch / && substr($0, 8)==b{print path}
            ')
            print_info "  Used by: $worktree_using"
            return 1
        fi
    fi

    return 0
}

# Cleanup orphaned worktree artifacts at build start
cleanup_orphaned_worktrees() {
    print_info "Checking for orphaned worktree artifacts..."

    local cleanup_count=0
    local skip_count=0

    # Find directories in .trees/ that aren't registered worktrees
    if [ -d "$TREES_DIR" ]; then
        for dir in "$TREES_DIR"/*; do
            [ -d "$dir" ] || continue
            local basename
            basename=$(basename "$dir")

            # Skip special directories
            [[ "$basename" == .* ]] && continue

            # Check if this is a registered worktree (use full path for exact matching)
            local full_path
            full_path=$(cd "$dir" && pwd)
            # Use grep -F for fixed-string matching to avoid regex interpretation of paths
            if ! git worktree list --porcelain 2>/dev/null | grep -F -q "worktree $full_path"; then
                # Not registered - it's orphaned
                print_warning "  Found orphaned directory: $basename"

                # Validate cleanup is safe
                if validate_cleanup_safe "$dir"; then
                    rm -rf "$dir"
                    print_success "  Removed orphaned directory: $basename"
                    cleanup_count=$((cleanup_count + 1))
                else
                    print_warning "  Skipped (has uncommitted changes): $basename"
                    skip_count=$((skip_count + 1))
                fi
            fi
        done
    fi

    if [ $cleanup_count -gt 0 ]; then
        print_success "Cleaned up $cleanup_count orphaned director(y/ies)"
    fi

    if [ $skip_count -gt 0 ]; then
        print_warning "Skipped $skip_count director(y/ies) with uncommitted changes"
        echo "  Review manually or commit/stash changes"
    fi

    if [ $cleanup_count -eq 0 ] && [ $skip_count -eq 0 ]; then
        print_success "No orphaned artifacts found"
    fi
}

# Rollback partially created worktrees on build failure
rollback_build() {
    local created_worktrees=("$@")

    if [ ${#created_worktrees[@]} -eq 0 ]; then
        return 0
    fi

    print_warning "Rolling back ${#created_worktrees[@]} partially created worktree(s)..."

    local rollback_count=0
    for worktree_info in "${created_worktrees[@]}"; do
        local worktree_path="${worktree_info%%|||*}"
        local branch="${worktree_info#*|||}"

        # Remove worktree
        if git worktree remove "$worktree_path" --force &>/dev/null; then
            print_success "  Removed worktree: $(basename "$worktree_path")"
        elif [ -d "$worktree_path" ]; then
            # Worktree not registered, remove directory
            rm -rf "$worktree_path"
            print_success "  Removed directory: $(basename "$worktree_path")"
        fi

        # Delete branch
        if git branch -D "$branch" &>/dev/null; then
            print_success "  Deleted branch: $branch"
        fi

        rollback_count=$((rollback_count + 1))
    done

    print_success "Rollback complete: $rollback_count worktree(s) cleaned up"
}
