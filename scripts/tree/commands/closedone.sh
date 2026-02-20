#!/bin/bash
#
# Script: commands/closedone.sh
# Purpose: Prune all local worktrees
# Created: 2026-01-28
# Description: Batch-remove all worktrees in .trees/ and clean up local branches

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR, WORKSPACE_ROOT

# /tree closedone [options]
# Prune all local worktrees
closedone_main() {
    local dry_run=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree closedone [--dry-run]"
                echo ""
                echo "Removes all local worktrees and cleans up branches."
                echo "Use --dry-run to preview without making changes."
                return 1
                ;;
        esac
    done

    if [ "$dry_run" = true ]; then
        print_header "[DRY RUN] /tree closedone - Prune All Worktrees"
    else
        print_header "/tree closedone - Prune All Worktrees"
    fi

    # Discover all worktrees
    local worktrees=()
    local worktree_branches=()

    if [ -d "$TREES_DIR" ]; then
        for dir in "$TREES_DIR"/*/ ; do
            [ -d "$dir/.git" ] || [ -f "$dir/.git" ] || continue

            local name
            name=$(basename "$dir")

            # Skip special directories
            [[ "$name" == .* ]] && continue

            local branch
            branch=$(cd "$dir" && git branch --show-current 2>/dev/null || echo "")

            worktrees+=("$name")
            worktree_branches+=("$branch")
        done
    fi

    if [ ${#worktrees[@]} -eq 0 ]; then
        print_info "No worktrees found to prune"
        return 0
    fi

    # Display what will be removed
    echo "Worktrees to remove:"
    echo ""
    for i in "${!worktrees[@]}"; do
        local name="${worktrees[$i]}"
        local branch="${worktree_branches[$i]}"
        local path="$TREES_DIR/$name"

        echo "  $((i+1)). $name"
        [ -n "$branch" ] && echo "     Branch: $branch"
        echo "     Path: $path"

        # Warn about uncommitted changes
        if (cd "$path" && [ -n "$(git status --porcelain 2>/dev/null)" ]); then
            print_warning "     Has uncommitted changes!"
        fi
    done
    echo ""

    if [ "$dry_run" = true ]; then
        echo "============================================================"
        print_info "[DRY RUN] Would remove ${#worktrees[@]} worktree(s)"
        print_info "Run without --dry-run to execute"
        return 0
    fi

    # Confirm
    if ! confirm_prompt "Remove all ${#worktrees[@]} worktree(s)?" "n"; then
        echo "Aborted."
        return 1
    fi
    echo ""

    # Move to workspace root before removing worktrees
    if ! cd "$WORKSPACE_ROOT"; then
        print_error "Failed to change to workspace root: $WORKSPACE_ROOT"
        return 1
    fi

    # Remove worktrees
    local success_count=0
    local failed_count=0

    for i in "${!worktrees[@]}"; do
        local name="${worktrees[$i]}"
        local branch="${worktree_branches[$i]}"
        local path="$TREES_DIR/$name"

        echo "[$((i+1))/${#worktrees[@]}] $name"

        # Remove worktree
        if git worktree remove "$path" --force 2>&1; then
            print_success "  Removed worktree"
        elif [ ! -d "$path" ]; then
            print_warning "  Worktree already removed"
        else
            print_error "  Failed to remove worktree"
            failed_count=$((failed_count + 1))
            echo ""
            continue
        fi

        # Delete local branch
        if [ -n "$branch" ]; then
            if git branch -d "$branch" 2>/dev/null; then
                print_success "  Deleted branch: $branch"
            elif git branch -D "$branch" 2>/dev/null; then
                print_warning "  Force-deleted branch: $branch"
            elif git rev-parse --verify "$branch" &>/dev/null; then
                print_warning "  Could not delete branch: $branch"
            else
                print_warning "  Branch already deleted: $branch"
            fi
        fi

        success_count=$((success_count + 1))
        echo ""
    done

    # Clean up stale worktree references
    git worktree prune 2>/dev/null || true

    # Summary
    echo "============================================================"
    echo "PRUNE SUMMARY"
    echo ""
    echo "  Removed: $success_count"
    if [ $failed_count -gt 0 ]; then
        echo "  Failed: $failed_count"
    fi
    echo ""
    echo "Note: Remote branches are preserved."
    echo "============================================================"

    echo ""
    echo "Note: closedone is mechanical-only (no AI wrap-up phases)."
    echo "For the full close flow (remember/learn/publish), use"
    echo "  /tree close  from inside each worktree individually."

    print_success "Worktree cleanup complete"
}
