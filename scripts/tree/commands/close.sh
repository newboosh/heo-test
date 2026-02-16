#!/bin/bash
#
# Script: commands/close.sh
# Purpose: Worktree completion commands
# Created: 2026-01-28
# Description: Close/complete worktrees with auto-commit, push, and PR creation

# Dependencies: lib/common.sh (print_* functions)
# Required variables: TREES_DIR, COMPLETED_DIR

# /tree close [incomplete]
# Complete work in current worktree
tree_close() {
    # Parse options
    local status="COMPLETE"
    local incomplete_flag=false

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
        echo "This command must be run from within a worktree"
        return 1
    fi

    if [ "$incomplete_flag" = true ]; then
        print_header "Saving Work Progress: $worktree_name (INCOMPLETE)"
    else
        print_header "Completing Work: $worktree_name"
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
            echo "Please stage and commit manually before closing:"
            echo "  git add -A"
            echo "  git commit -m 'Your message'"
            echo "  /tree close"
            return 1
        fi

        # Generate commit message based on status
        local commit_msg
        if [ "$incomplete_flag" = true ]; then
            commit_msg="wip: ${worktree_name//-/ } - work in progress

Automatically committed by /tree close incomplete

Co-Authored-By: Steve Glen, Claude Code"
        else
            commit_msg="feat: ${worktree_name//-/ } complete

Automatically committed by /tree close

Co-Authored-By: Steve Glen, Claude Code"
        fi

        # Commit changes
        if git commit -m "$commit_msg" 2>/dev/null; then
            print_success "Changes auto-committed successfully"

            # Show what was committed
            local committed_files=$(git diff --name-only HEAD~1 2>/dev/null | wc -l | tr -d ' ')
            echo "  Files committed: $committed_files"

            # Show commit details
            echo ""
            echo "Commit details:"
            git --no-pager log -1 --oneline
            echo ""
        else
            print_error "Failed to auto-commit changes"
            echo ""
            echo "Please commit manually before closing:"
            echo "  git add -A"
            echo "  git commit -m 'Your message'"
            echo "  /tree close"
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
    local files_created=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^A" || true)
    local files_modified=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^M" || true)
    local files_deleted=$(git diff --name-status "$base_branch..$branch" 2>/dev/null | grep -c "^D" || true)
    local commit_count=$(git log --oneline "$base_branch..$branch" 2>/dev/null | wc -l | tr -d ' ')

    echo "  Files created: $files_created"
    echo "  Files modified: $files_modified"
    echo "  Files deleted: $files_deleted"
    echo "  Commits: $commit_count"
    echo ""

    # Determine target directory based on status
    local target_dir
    if [ "$incomplete_flag" = true ]; then
        target_dir="$TREES_DIR/.incomplete"
    else
        target_dir="$COMPLETED_DIR"
    fi
    mkdir -p "$target_dir"

    # Extract original task description if available
    local original_description=""
    local task_context_file="$worktree_root/.claude-task-context.md"
    if [ -f "$task_context_file" ]; then
        original_description=$(grep -A 5 "^## Task Description" "$task_context_file" | tail -n +2 | head -n 3)
    fi

    # Generate synopsis
    local timestamp=$(date +%Y%m%d-%H%M%S)
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
2. Run /tree closedone --full-cycle to start the next cycle
3. The task description will be preserved for continuation

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
3. Run /tree closedone to prune local worktrees

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
        echo ""
        echo "Next Steps:"
        echo "  1. Work on other features"
        echo "  2. Run /tree closedone when ready to prune worktrees"
        echo "  3. This feature will be auto-staged in the new cycle"
    else
        echo "Next Steps:"
        echo "  1. Create PR on GitHub: gh pr create --fill"
        echo "  2. Wait for code review and merge on GitHub"
        echo "  3. Run /tree closedone to prune local worktrees"
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
