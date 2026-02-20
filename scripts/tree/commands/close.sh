#!/bin/bash
#
# Script: commands/close.sh
# Purpose: Remove a worktree
# Created: 2026-01-28
# Modified: 2026-02-19
# Description: Close a worktree by verifying merge status, then removing it
#              and cleaning up the local branch. Supports --check-only for
#              SKILL.md orchestration (verify merge, then exit).

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR

# /tree close [--check-only] [--force]
# Remove the current worktree (with merge verification)
tree_close() {
    local check_only=false
    local force=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                check_only=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree close [--check-only] [--force]"
                return 1
                ;;
        esac
    done

    # Detect if we're in a worktree using git rev-parse
    local worktree_root
    worktree_root=$(git rev-parse --show-toplevel 2>/dev/null)
    local worktree_name=""

    if [ -z "$worktree_root" ]; then
        print_error "Not in a git repository"
        echo "This command must be run from within a worktree"
        return 1
    fi

    # Check if worktree_root contains /.trees/ (i.e., is inside our worktree directory)
    if [[ "$worktree_root" == *"/.trees/"* ]]; then
        worktree_name=$(basename "$worktree_root")
    else
        print_error "Not in a worktree directory"
        echo "This command must be run from within a worktree"
        return 1
    fi

    local branch
    branch=$(git branch --show-current)

    if [ -z "$branch" ]; then
        print_error "Worktree is in detached HEAD state — cannot verify merge"
        return 1
    fi

    print_header "Closing Worktree: $worktree_name"
    echo "Worktree: $worktree_name"
    echo "Branch: $branch"
    echo "Path: $worktree_root"
    echo ""

    # ── Merge verification ──────────────────────────────────────────────
    if [ "$force" = true ]; then
        print_warning "Skipping merge verification (--force)"
    else
        print_info "Checking merge status..."
        git fetch origin main --quiet 2>/dev/null || git fetch origin --quiet 2>/dev/null || true

        if git merge-base --is-ancestor "origin/$branch" origin/main 2>/dev/null; then
            print_success "Branch '$branch' is merged into remote main"
        else
            print_warning "Branch '$branch' has not been merged into remote main."
            echo "Push and merge your PR first, then run /tree close."
            echo "To close anyway (e.g., abandoned branch): /tree close --force"
            return 1
        fi
    fi

    # If --check-only, stop here (SKILL.md will orchestrate AI phases next)
    if [ "$check_only" = true ]; then
        echo ""
        print_info "Merge verified. Exiting (--check-only mode)."
        return 0
    fi

    # ── Mechanical close ────────────────────────────────────────────────

    # Warn if there are uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Uncommitted changes detected!"
        echo ""
        git status --short
        echo ""
        if ! confirm_prompt "Discard uncommitted changes and close anyway?" "n"; then
            echo "Aborted. Commit or stash your changes first."
            return 1
        fi
    fi

    # Move out of the worktree before removing it
    local main_worktree
    main_worktree=$(git worktree list --porcelain | head -1 | sed 's/^worktree //')
    cd "$main_worktree" || cd "$HOME"

    # Remove the worktree
    print_info "Removing worktree..."
    if git worktree remove "$worktree_root" --force 2>&1; then
        print_success "Worktree removed: $worktree_name"
    else
        print_error "Failed to remove worktree"
        echo "  Try manually: git worktree remove \"$worktree_root\" --force"
        return 1
    fi

    # Clean up local branch
    if git branch -d "$branch" 2>/dev/null; then
        print_success "Local branch deleted: $branch"
    elif git branch -D "$branch" 2>/dev/null; then
        print_success "Local branch force-deleted: $branch"
    else
        print_warning "Could not delete local branch: $branch (may already be deleted)"
    fi

    echo ""
    print_success "Worktree '$worktree_name' closed"
}
