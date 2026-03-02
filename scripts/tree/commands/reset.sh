#!/bin/bash
#
# Script: commands/reset.sh
# Purpose: Complete worktree reset — ship it, AI wrapup, mechanical reset
# Created: 2026-02-19
# Modified: 2026-02-20
# Description: Single "end of task" command combining close + wrapup + reset.
#              SKILL.md orchestrates the full 6-step sequence; this script
#              handles the bash-side steps (ship-it, commit learnings, mechanical reset).
#
# Flags:
#   incomplete         WIP save only (commit + push + incomplete synopsis, no wrapup, no reset)
#   --all              Batch mechanical reset only (all worktrees)
#   --force            Discard uncommitted changes, skip confirmations
#   --rename <name>    Rename branch after reset
#   --mechanical-only  Skip ship-it, go straight to git reset (used by SKILL.md step 6)

# Dependencies: lib/common.sh (print_* functions), lib/git-safety.sh
# Required variables: WORKSPACE_ROOT, TREES_DIR

# Detect which remote is available (prefer 'source', fall back to 'origin')
_reset_detect_remote() {
    if git -C "$WORKSPACE_ROOT" remote get-url source &>/dev/null; then
        echo "source"
    elif git -C "$WORKSPACE_ROOT" remote get-url origin &>/dev/null; then
        echo "origin"
    else
        echo ""
    fi
}

# Reset a single worktree to remote/main
# Usage: _reset_single_worktree <worktree_path> <force> <new_name> <remote>
_reset_single_worktree() {
    local worktree_path="$1"
    local force="$2"
    local new_name="$3"
    local remote="$4"
    local wt_name
    wt_name="$(basename "$worktree_path")"

    # Validate it's actually a worktree (worktrees have a .git file, not directory)
    if [ ! -f "$worktree_path/.git" ] && [ ! -d "$worktree_path/.git" ]; then
        print_error "  $wt_name: Not a git worktree — skipping"
        return 1
    fi

    # Get current branch
    local branch
    branch=$(git -C "$worktree_path" branch --show-current 2>/dev/null || echo "")
    if [ -z "$branch" ]; then
        print_warning "  $wt_name: Detached HEAD — skipping"
        return 1
    fi

    # Check for uncommitted changes
    local dirty
    dirty=$(git -C "$worktree_path" status --porcelain 2>/dev/null)
    if [ -n "$dirty" ] && [ "$force" != "true" ]; then
        print_error "  $wt_name [$branch]: Has uncommitted changes — use --force to discard"
        return 1
    fi

    # Fetch latest main (once per invocation, tracked by RESET_FETCHED)
    if [ "$RESET_FETCHED" != "true" ]; then
        print_info "Fetching $remote/main..."
        if ! git -C "$WORKSPACE_ROOT" fetch "$remote" main --quiet 2>/dev/null; then
            print_error "Failed to fetch $remote/main — check network and credentials."
            return 1
        fi
        RESET_FETCHED=true
    fi

    # Reset branch to remote/main
    if ! git -C "$worktree_path" reset --hard --quiet "$remote/main" 2>/dev/null; then
        print_error "  $wt_name [$branch]: git reset --hard failed"
        return 1
    fi

    # Clean untracked files from old work
    git -C "$worktree_path" clean -fd --quiet 2>/dev/null

    # Handle rename if requested
    if [ -n "$new_name" ]; then
        local new_branch="$new_name"
        if git -C "$worktree_path" branch -m "$branch" "$new_branch" 2>/dev/null; then
            # Update PURPOSE.md if it exists
            if [ -f "$worktree_path/PURPOSE.md" ]; then
                local tmp_purpose
                tmp_purpose=$(mktemp)
                sed "s|**Branch:** .*|**Branch:** $new_branch|" "$worktree_path/PURPOSE.md" > "$tmp_purpose" 2>/dev/null && mv "$tmp_purpose" "$worktree_path/PURPOSE.md"
            fi
            # Update CLAUDE.md if it exists
            if [ -f "$worktree_path/CLAUDE.md" ]; then
                local tmp_claude
                tmp_claude=$(mktemp)
                sed "s|**Branch**: .*|**Branch**: \`$new_branch\`|" "$worktree_path/CLAUDE.md" > "$tmp_claude" 2>/dev/null && mv "$tmp_claude" "$worktree_path/CLAUDE.md"
            fi
            print_success "  $wt_name: Reset to $remote/main + renamed $branch → $new_branch"
        else
            print_warning "  $wt_name: Reset OK but rename failed (branch '$new_branch' may already exist)"
        fi
    else
        local short_sha
        short_sha=$(git -C "$worktree_path" rev-parse --short HEAD 2>/dev/null)
        print_success "  $wt_name [$branch]: Reset to $remote/main ($short_sha)"
    fi

    return 0
}

# Ship It: auto-commit, push, synopsis, PR offer
# This is the former tree_close() ship-it logic adapted for the reset flow
tree_reset_ship_it() {
    local incomplete_flag=false
    local status="COMPLETE"

    if [[ "$1" == "incomplete" ]]; then
        incomplete_flag=true
        status="INCOMPLETE"
    fi

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
        echo "This command must be run from within a worktree under .trees/"
        return 1
    fi

    if [ "$incomplete_flag" = true ]; then
        print_header "Saving Work Progress: $worktree_name (INCOMPLETE)"
    else
        print_header "Ship It: $worktree_name"
    fi

    # Get branch info (declare and assign separately to avoid masking return values)
    local branch
    branch=$(git branch --show-current)
    local base_branch
    base_branch=$(git config --get "branch.$branch.merge" 2>/dev/null || true)
    base_branch="${base_branch#refs/heads/}"
    # If base_branch is empty, default to "main"
    if [ -z "$base_branch" ]; then
        base_branch="main"
    fi

    echo "Worktree: $worktree_name"
    echo "Branch: $branch"
    echo "Base: $base_branch"
    if [ "$incomplete_flag" = true ]; then
        echo "Status: [!] INCOMPLETE - will continue in next cycle"
    fi
    echo ""

    # AUTO-COMMIT: Check for uncommitted changes and commit them automatically
    print_info "Checking for uncommitted changes..."

    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Uncommitted changes detected. Auto-committing..."
        echo ""

        # Stage all changes (tracked and untracked)
        if ! git add -A 2>/dev/null; then
            print_error "Failed to stage changes"
            echo ""
            echo "Please stage and commit manually before resetting:"
            echo "  git add -A"
            echo "  git commit -m 'Your message'"
            echo "  /tree reset"
            return 1
        fi

        # Generate commit message based on status
        local commit_msg
        if [ "$incomplete_flag" = true ]; then
            commit_msg="wip: ${worktree_name//-/ } - work in progress

Automatically committed by /tree reset incomplete

Co-Authored-By: Steve Glen <therealstevenglen@gmail.com>
Co-Authored-By: Claude Code <noreply@anthropic.com>"
        else
            commit_msg="feat: ${worktree_name//-/ } complete

Automatically committed by /tree reset

Co-Authored-By: Steve Glen <therealstevenglen@gmail.com>
Co-Authored-By: Claude Code <noreply@anthropic.com>"
        fi

        # Commit changes
        if git commit -m "$commit_msg" 2>/dev/null; then
            print_success "Changes auto-committed successfully"

            # Show what was committed
            local committed_files
            committed_files=$(git diff --name-only HEAD~1 2>/dev/null | wc -l | tr -d ' ')
            echo "  Files committed: $committed_files"

            # Show commit details
            echo ""
            echo "Commit details:"
            git --no-pager log -1 --oneline
            echo ""
        else
            print_error "Failed to auto-commit changes"
            echo ""
            echo "Please commit manually before resetting:"
            echo "  git add -A"
            echo "  git commit -m 'Your message'"
            echo "  /tree reset"
            return 1
        fi
    else
        print_success "No uncommitted changes"
        echo ""
    fi

    # PUSH TO REMOTE: Push branch to origin for GitHub PR review
    print_info "Pushing branch to remote..."

    # Ensure GitHub auth is synced (if available)
    if type github_auth_sync &>/dev/null; then
        if ! GITHUB_AUTH_FORCE=1 github_auth_sync; then
            print_warning "GitHub auth sync failed; push may require manual login"
        fi
    fi

    if git push -u origin "$branch" 2>&1; then
        print_success "Branch pushed to origin: $branch"
        echo ""
    else
        print_warning "Failed to push to remote (may already exist or no remote configured)"
        echo "  You can push manually: git push -u origin $branch"
        echo ""
    fi

    # Analyze changes
    print_info "Analyzing changes..."
    local files_created
    files_created=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^A" || true)
    local files_modified
    files_modified=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^M" || true)
    local files_deleted
    files_deleted=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^D" || true)
    local commit_count
    commit_count=$(git log --oneline "$base_branch..$branch" 2>/dev/null | wc -l | tr -d ' ')

    echo "  Files created: $files_created"
    echo "  Files modified: $files_modified"
    echo "  Files deleted: $files_deleted"
    echo "  Commits: $commit_count"
    echo ""

    # Determine target directory based on status
    local completed_dir="$TREES_DIR/.completed"
    local target_dir
    if [ "$incomplete_flag" = true ]; then
        target_dir="$TREES_DIR/.incomplete"
    else
        target_dir="$completed_dir"
    fi
    mkdir -p "$target_dir"

    # Extract original task description if available
    local original_description=""
    local purpose_file="$worktree_root/PURPOSE.md"
    if [ -f "$purpose_file" ]; then
        original_description=$(grep -A 5 "^## Objective" "$purpose_file" | tail -n +2 | head -n 3)
    fi

    # Generate synopsis
    local timestamp
    timestamp=$(date +%Y%m%d-%H%M%S)
    local synopsis_file="$target_dir/${worktree_name}-synopsis-${timestamp}.md"

    if [ "$incomplete_flag" = true ]; then
        # Generate INCOMPLETE synopsis
        cat > "$synopsis_file" << EOF
# Work In Progress: ${worktree_name//-/ }

# Branch: $branch
# Base: $base_branch
# Closed: $(date +"%Y-%m-%d %H:%M:%S")
# Status: INCOMPLETE
# Resume: This feature needs to continue in the next development cycle

## Original Task Description

$original_description

## Progress Summary

Work has been started on this feature but requires additional work to complete.

## Changes So Far

- Files created: $files_created
- Files modified: $files_modified
- Files deleted: $files_deleted
- Total commits: $commit_count

## Files Changed

$(git diff --name-status "$base_branch..$branch" 2>/dev/null || echo "No changes detected")

## Commit History

$(git log --oneline "$base_branch..$branch" 2>/dev/null || echo "No commits")

## Remaining Work

- [ ] Additional tasks to be defined in next cycle
- [ ] Complete feature implementation
- [ ] Add comprehensive tests
- [ ] Update documentation

## Next Steps

1. This feature will be automatically staged in the next development cycle
2. The task description will be preserved for continuation

EOF
    else
        # Generate COMPLETE synopsis
        cat > "$synopsis_file" << EOF
# Work Completed: ${worktree_name//-/ }

# Branch: $branch
# Base: $base_branch
# Completed: $(date +"%Y-%m-%d %H:%M:%S")
# Status: COMPLETE

## Summary

Work completed in worktree: $worktree_name

## Changes

- Files created: $files_created
- Files modified: $files_modified
- Files deleted: $files_deleted
- Total commits: $commit_count

## Files Changed

$(git diff --name-status "$base_branch..$branch" 2>/dev/null || echo "No changes detected")

## Commit History

$(git log --oneline "$base_branch..$branch" 2>/dev/null || echo "No commits")

## Next Steps

1. Review the PR on GitHub
2. Merge via GitHub after code review

EOF
    fi

    print_success "Synopsis generated: $synopsis_file"
    echo ""
    echo "============================================================"
    if [ "$incomplete_flag" = true ]; then
        echo "[!] Work Progress Saved: $worktree_name (INCOMPLETE)"
    else
        echo "Work Summary: $worktree_name"
    fi
    echo "============================================================"
    echo ""
    echo "Changes:"
    echo "  - Created: $files_created files"
    echo "  - Modified: $files_modified files"
    echo "  - Deleted: $files_deleted files"
    echo "  - Commits: $commit_count"
    echo ""
    echo "============================================================"
    echo ""
    echo "Documentation: $synopsis_file"
    echo ""
    if [ "$incomplete_flag" = true ]; then
        echo "[!] Status: INCOMPLETE"
        echo "  This feature will automatically continue in the next development cycle"
    else
        echo "Next Steps:"
        echo "  1. Create PR on GitHub: gh pr create --fill"
        echo "  2. Wait for code review and merge on GitHub"
        echo ""
        print_success "Branch pushed to origin - ready for PR review"
    fi

    # Offer to create PR
    if [ "$incomplete_flag" = false ] && command -v gh &> /dev/null; then
        echo ""
        if confirm_prompt "Create GitHub PR now?" "n"; then
            print_info "Creating GitHub PR..."
            local pr_title="feat: ${worktree_name//-/ }"
            local pr_body="## Summary
Branch: \`$branch\`

## Changes
- Files created: $files_created
- Files modified: $files_modified
- Files deleted: $files_deleted
- Commits: $commit_count

## Files Changed
\`\`\`
$(git diff --name-status "$base_branch..$branch" 2>/dev/null | head -20 || echo "No changes detected")
\`\`\`

---
Generated with [Claude Code](https://claude.com/claude-code)"

            if gh pr create --title "$pr_title" --body "$pr_body" 2>&1; then
                print_success "PR created successfully!"
            else
                print_warning "Failed to create PR. Create manually: gh pr create --fill"
            fi
        fi
    fi
}

# /tree reset [options]
# Main entry point — parses flags, dispatches to appropriate handler
tree_reset() {
    local reset_all=false
    local new_name=""
    local force=false
    local mechanical_only=false
    local incomplete_flag=""

    while [ $# -gt 0 ]; do
        case "$1" in
            --all)
                reset_all=true
                shift
                ;;
            --rename)
                shift
                if [ -z "${1:-}" ] || [[ "${1:-}" == --* ]]; then
                    print_error "--rename requires a name argument"
                    return 1
                fi
                new_name="$1"
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --mechanical-only)
                mechanical_only=true
                shift
                ;;
            incomplete)
                incomplete_flag="incomplete"
                shift
                ;;
            --help|-h)
                echo "Usage: /tree reset [options]"
                echo ""
                echo "Complete worktree task: ship it, AI wrapup, mechanical reset."
                echo "SKILL.md orchestrates the full 6-step sequence."
                echo ""
                echo "Options:"
                echo "  incomplete         WIP save only (commit + push, no wrapup, no reset)"
                echo "  --all              Batch mechanical reset only (all worktrees)"
                echo "  --force            Discard uncommitted changes, skip confirmations"
                echo "  --rename <name>    Rename branch after reset"
                echo "  --mechanical-only  Skip ship-it, go straight to git reset (used by SKILL.md)"
                echo "  --help, -h         Show this help"
                return 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree reset [--all] [--force] [--rename <name>] [--mechanical-only] [incomplete]"
                return 1
                ;;
        esac
    done

    # --all: batch mechanical reset of all worktrees
    if [ "$reset_all" = true ]; then
        print_header "Worktree Reset (All)"

        local remote
        remote=$(_reset_detect_remote)
        if [ -z "$remote" ]; then
            print_error "No usable remote found. Expected 'source' or 'origin'."
            return 1
        fi

        if [ -n "$new_name" ]; then
            print_error "--rename cannot be used with --all"
            return 1
        fi

        if [ ! -d "$TREES_DIR" ]; then
            print_warning "No .trees/ directory found. Nothing to reset."
            return 0
        fi

        # Fetch once for all worktrees
        print_info "Fetching $remote/main..."
        if ! git -C "$WORKSPACE_ROOT" fetch "$remote" main --quiet 2>/dev/null; then
            print_error "Failed to fetch $remote/main — check network and credentials."
            return 1
        fi
        RESET_FETCHED=true

        local success=0
        local failed=0
        local total=0

        for wt_path in "$TREES_DIR"/*/; do
            local wt_name
            wt_name="$(basename "$wt_path")"
            # Skip hidden/meta dirs like .completed, .archived, .build-history
            [[ "$wt_name" == .* ]] && continue
            [ -d "$wt_path/.git" ] || [ -f "$wt_path/.git" ] || continue
            total=$((total + 1))

            if _reset_single_worktree "$wt_path" "$force" "" "$remote"; then
                success=$((success + 1))
            else
                failed=$((failed + 1))
            fi
        done

        echo ""
        if [ $total -eq 0 ]; then
            print_warning "No worktrees found to reset."
        elif [ $failed -eq 0 ]; then
            print_success "All $success worktree(s) reset to $remote/main."
        else
            print_warning "$failed of $total worktree(s) failed to reset."
        fi

        unset RESET_FETCHED
        return 0
    fi

    # --mechanical-only: skip ship-it, just do git reset (called by SKILL.md step 6)
    if [ "$mechanical_only" = true ]; then
        print_header "Mechanical Reset"

        local remote
        remote=$(_reset_detect_remote)
        if [ -z "$remote" ]; then
            print_error "No usable remote found. Expected 'source' or 'origin'."
            return 1
        fi

        local current_dir
        current_dir=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

        if [[ "$current_dir" != "$TREES_DIR/"* ]]; then
            print_error "Not in a worktree directory"
            echo ""
            echo "  From root, use:  /tree reset --all"
            echo "  From a worktree: /tree reset --mechanical-only"
            return 1
        fi

        _reset_single_worktree "$current_dir" "$force" "$new_name" "$remote"
        local rc=$?
        unset RESET_FETCHED
        return $rc
    fi

    # incomplete: WIP save only (commit + push + incomplete synopsis, no wrapup, no reset)
    if [ -n "$incomplete_flag" ]; then
        tree_reset_ship_it "incomplete"
        return $?
    fi

    # Default: run ship-it (step 1), then exit so SKILL.md handles steps 2-6
    tree_reset_ship_it
}
