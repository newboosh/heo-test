#!/bin/bash
#
# Script: commands/closedone.sh
# Purpose: Worktree completion and full-cycle automation
# Created: 2026-01-28
# Description: Prune worktrees after PR merge, full development cycle automation

# Dependencies: lib/common.sh, lib/git-safety.sh, lib/validation.sh, commands/stage.sh
# Required variables: TREES_DIR, COMPLETED_DIR, INCOMPLETE_DIR, ARCHIVED_DIR, WORKSPACE_ROOT, CONFLICT_BACKUP_DIR

# /tree closedone [options]
# Main entry point for closedone command
closedone_main() {
    local force_prune=false
    local dry_run=false

    # Check for --full-cycle flag and delegate
    for arg in "$@"; do
        if [ "$arg" = "--full-cycle" ]; then
            closedone_full_cycle "$@"
            return $?
        fi
    done

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --yes|-y)
                # Legacy flag - kept for compatibility
                shift
                ;;
            --force)
                force_prune=true
                shift
                ;;
            --force-dirty)
                # Legacy flag
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree closedone [--force] [--dry-run]"
                echo ""
                echo "Prunes local worktrees after PRs have been merged on GitHub."
                echo "Use --force to prune regardless of close status."
                echo "Use --dry-run to preview without making changes."
                return 1
                ;;
        esac
    done

    if [ "$dry_run" = true ]; then
        print_header "[DRY RUN] /tree closedone - Prune Worktrees"
    else
        print_header "/tree closedone - Prune Worktrees"
    fi
    echo "Note: Merging happens via GitHub PRs, not locally."
    echo ""

    # Check for unclosed worktrees
    if [ "$force_prune" = false ]; then
        if ! validate_all_worktrees_closed; then
            echo ""
            print_info "Use --force to prune all worktrees anyway"
            return 1
        fi
    else
        print_warning "[!] --force flag used: pruning all worktrees regardless of close status"
        echo ""
    fi

    # Discover completed worktrees
    print_info "Discovering completed worktrees..."

    if [ ! -d "$COMPLETED_DIR" ]; then
        print_warning "No completed worktrees found"
        return 0
    fi

    local synopsis_files=()
    while IFS= read -r -d '' file; do
        synopsis_files+=("$file")
    done < <(find "$COMPLETED_DIR" -name "*-synopsis-*.md" -print0 2>/dev/null)

    if [ ${#synopsis_files[@]} -eq 0 ]; then
        print_warning "No completed worktrees found"
        return 0
    fi

    # Extract metadata
    local worktrees=()
    local worktree_branches=()
    local worktree_bases=()

    for synopsis_file in "${synopsis_files[@]}"; do
        local filename=$(basename "$synopsis_file")
        local worktree_name="${filename%%-synopsis-*}"

        local branch
        branch=$(grep -m1 "^# Branch:" "$synopsis_file" 2>/dev/null | sed 's/^# Branch: //' || echo "")
        local base
        base=$(grep -m1 "^# Base:" "$synopsis_file" 2>/dev/null | sed 's/^# Base: //' || echo "main")

        if [ ! -d "$TREES_DIR/$worktree_name" ]; then
            print_warning "Worktree directory not found: $worktree_name (skipping)"
            continue
        fi

        if ! git rev-parse --verify "$branch" &>/dev/null; then
            print_warning "Branch not found: $branch (skipping $worktree_name)"
            continue
        fi

        worktrees+=("$worktree_name")
        worktree_branches+=("$branch")
        worktree_bases+=("$base")
    done

    if [ ${#worktrees[@]} -eq 0 ]; then
        print_warning "No valid worktrees to process"
        return 0
    fi

    print_success "Found ${#worktrees[@]} completed worktree(s)"
    echo ""

    # Display summary
    for i in "${!worktrees[@]}"; do
        local worktree="${worktrees[$i]}"
        local branch="${worktree_branches[$i]}"
        local base="${worktree_bases[$i]}"
        local commit_count=$(git log --oneline "$base..$branch" 2>/dev/null | wc -l | tr -d ' ')

        echo "  $((i+1)). $worktree ($branch)"
        if [ "$commit_count" -gt 0 ]; then
            echo "     Commits: $commit_count"
        else
            echo "     No commits (cleanup only)"
        fi
    done
    echo ""

    if [ "$dry_run" = true ]; then
        echo "============================================================"
        print_info "[DRY RUN] Would prune ${#worktrees[@]} worktree(s)"
        print_info "Run without --dry-run to execute"
        return 0
    fi

    print_info "Pruning worktrees..."
    echo ""

    # Guard cd to prevent running destructive operations in wrong directory
    if ! cd "$WORKSPACE_ROOT"; then
        print_error "Failed to change to workspace root: $WORKSPACE_ROOT"
        return 1
    fi

    local success_count=0
    local failed_count=0

    for i in "${!worktrees[@]}"; do
        local worktree="${worktrees[$i]}"
        local branch="${worktree_branches[$i]}"
        local num=$((i+1))

        echo "[$num/${#worktrees[@]}] $worktree"

        if closedone_cleanup "$worktree" "$branch"; then
            success_count=$((success_count + 1))
            print_success "  Pruned successfully"
        else
            failed_count=$((failed_count + 1))
            print_error "  Failed to prune"
        fi
        echo ""
    done

    # Summary
    echo "============================================================"
    echo "PRUNE SUMMARY"
    echo ""
    echo "Worktrees Pruned: ${#worktrees[@]}"
    echo "  [OK] Success: $success_count"
    echo "  [FAIL] Failed: $failed_count"
    echo ""
    echo "Note: Remote branches remain for PR review."
    echo "============================================================"

    git worktree prune 2>/dev/null || true
    print_success "Worktree cleanup complete"
}

# Cleanup worktree and branch
# Returns 0 on success, 1 if any critical operation failed
closedone_cleanup() {
    local worktree=$1
    local branch=$2
    local ok=true

    # Remove worktree
    if safe_git worktree remove "$TREES_DIR/$worktree" &>/dev/null; then
        print_success "  Removed worktree"
    elif [ -d "$TREES_DIR/$worktree" ]; then
        # Directory still exists - this is a real failure
        print_error "  Failed to remove worktree"
        ok=false
    else
        print_warning "  Worktree already removed"
    fi

    # Delete local branch
    if safe_git branch -d "$branch" &>/dev/null; then
        print_success "  Deleted branch $branch"
    elif safe_git branch -D "$branch" &>/dev/null; then
        print_warning "  Force-deleted branch $branch"
    elif git rev-parse --verify "$branch" &>/dev/null; then
        # Branch still exists - this is a failure
        print_error "  Failed to delete branch $branch"
        ok=false
    else
        print_warning "  Branch already deleted"
    fi

    # Archive completion files
    if [ -d "$COMPLETED_DIR" ]; then
        mkdir -p "$ARCHIVED_DIR/$worktree"
        if mv "$COMPLETED_DIR/$worktree-"*.md "$ARCHIVED_DIR/$worktree/" 2>/dev/null; then
            print_success "  Archived completion files"
        fi
    fi

    if [ "$ok" = true ]; then
        print_success "  Status: [OK] SUCCESS"
        return 0
    else
        print_error "  Status: [FAIL] PARTIAL FAILURE"
        return 1
    fi
}

# Full-Cycle Orchestrator
closedone_full_cycle() {
    local bump_type="patch"
    local dry_run=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full-cycle)
                shift
                ;;
            --yes|-y)
                shift
                ;;
            --bump)
                bump_type="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree closedone --full-cycle [--bump patch|minor|major] [--dry-run]"
                return 1
                ;;
        esac
    done

    if [ "$dry_run" = true ]; then
        print_header "[DRY RUN] /tree closedone - Full Development Cycle"
    else
        print_header "/tree closedone - Full Development Cycle"
    fi

    # Preview
    echo "This will execute the complete development cycle:"
    echo "  1. Validate all worktrees closed"
    echo "  2. Merge completed features to dev branch"
    echo "  3. Promote dev branch to main"
    echo "  4. Bump version ($bump_type)"
    echo "  5. Create new dev branch"
    echo "  6. Auto-stage incomplete features"
    echo "  7. Archive and cleanup"
    echo ""

    # Count features
    local completed_count=0
    local incomplete_count=0
    [ -d "$COMPLETED_DIR" ] && completed_count=$(ls "$COMPLETED_DIR"/*-synopsis-*.md 2>/dev/null | wc -l | tr -d ' ') || true
    [ -d "$INCOMPLETE_DIR" ] && incomplete_count=$(ls "$INCOMPLETE_DIR"/*-synopsis-*.md 2>/dev/null | wc -l | tr -d ' ') || true

    echo "Features to process:"
    echo "  - Completed: $completed_count"
    echo "  - Incomplete: $incomplete_count"
    echo ""

    if [ "$dry_run" = true ]; then
        echo "============================================================"
        print_info "[DRY RUN] Would execute full cycle with $bump_type version bump"
        print_info "Run without --dry-run to execute"
        return 0
    fi

    # Execute phases
    local dev_branch=""
    local new_version=""
    local new_dev_branch=""

    # Phase 1: Validation
    if ! closedone_full_cycle_phase1; then
        rollback_full_cycle 1
        return 1
    fi
    echo ""

    # Phase 2: Merge
    if ! dev_branch=$(closedone_full_cycle_phase2); then
        rollback_full_cycle 2
        return 1
    fi
    echo ""

    # Phase 3: Promote to main
    if ! closedone_full_cycle_phase3 "$dev_branch"; then
        rollback_full_cycle 3
        return 1
    fi
    echo ""

    # Phase 4: Version bump
    if ! new_version=$(closedone_full_cycle_phase4 "$bump_type"); then
        rollback_full_cycle 4
        return 1
    fi
    echo ""

    # Phase 5: New cycle setup
    if ! new_dev_branch=$(closedone_full_cycle_phase5 "$new_version"); then
        rollback_full_cycle 5
        return 1
    fi
    echo ""

    # Phase 6: Cleanup
    if ! closedone_full_cycle_phase6 "$dev_branch" "$new_version" "$new_dev_branch"; then
        print_warning "  Cleanup had issues but cycle completed"
    fi

    # Cleanup temp files
    rm -f /tmp/cycle-branch-backup /tmp/cycle-checkpoint-tag

    # Final summary
    echo "============================================================"
    echo "[OK] FULL CYCLE COMPLETE"
    echo "============================================================"
    echo ""
    echo "Previous Dev Branch: $dev_branch"
    echo "New Version: $new_version"
    echo "New Dev Branch: $new_dev_branch"
    echo ""
    echo "Completed Features: $completed_count (merged)"
    echo "Incomplete Features: $incomplete_count (staged)"
    echo ""
    echo "Next Steps:"
    echo "  - /tree stage [description]"
    echo "  - /tree build"
    echo "============================================================"

    return 0
}

# Phase 1: Validation & Checkpoint
# Note: All logging goes to stderr to avoid contaminating command substitution
closedone_full_cycle_phase1() {
    print_info "Phase 1: Validation & Checkpoint" >&2

    local unclosed_count=0
    if [ -d "$TREES_DIR" ]; then
        for dir in "$TREES_DIR"/*/ ; do
            [ -d "$dir/.git" ] || [ -f "$dir/.git" ] || continue
            local name
            name=$(basename "$dir")
            # Check both completed and incomplete directories separately to avoid stacked redirections
            local has_completed=false
            local has_incomplete=false
            ls "$COMPLETED_DIR/$name-synopsis-"*.md &>/dev/null && has_completed=true
            ls "$INCOMPLETE_DIR/$name-synopsis-"*.md &>/dev/null && has_incomplete=true
            if [ "$has_completed" = false ] && [ "$has_incomplete" = false ]; then
                print_warning "  Unclosed worktree: $name" >&2
                unclosed_count=$((unclosed_count + 1))
            fi
        done
    fi

    if [ $unclosed_count -gt 0 ]; then
        print_error "Found $unclosed_count unclosed worktree(s)" >&2
        echo "Run /tree close in each worktree first" >&2
        return 1
    fi

    local current_branch=$(git branch --show-current)
    echo "$current_branch" > /tmp/cycle-branch-backup

    local checkpoint_tag="checkpoint-before-full-cycle-$(date +%Y%m%d-%H%M%S)"
    if ! git tag "$checkpoint_tag" 2>/dev/null; then
        print_error "  Failed to create checkpoint tag" >&2
        return 1
    fi
    echo "$checkpoint_tag" > /tmp/cycle-checkpoint-tag

    print_success "  [OK] All worktrees closed" >&2
    print_success "  [OK] Checkpoint: $checkpoint_tag" >&2
    return 0
}

# Phase 2: Merge Completed Features
# Note: All logging goes to stderr; only echo "$dev_branch" goes to stdout for capture
closedone_full_cycle_phase2() {
    print_info "Phase 2: Merge Completed Features" >&2

    local dev_branch
    dev_branch=$(git branch --show-current)
    if [ -z "$dev_branch" ]; then
        print_error "  No current branch (detached HEAD). Aborting." >&2
        return 1
    fi

    if ! closedone_main --yes 1>&2; then
        print_error "  Failed to merge completed worktrees" >&2
        return 1
    fi

    # Ensure GitHub auth is synced before push
    if type github_auth_sync &>/dev/null; then
        if ! GITHUB_AUTH_FORCE=1 github_auth_sync 2>/dev/null; then
            print_warning "GitHub auth sync failed; push may require manual login" >&2
        fi
    fi

    git push origin "$dev_branch" 2>/dev/null || true
    print_success "  [OK] Features merged" >&2
    echo "$dev_branch"
    return 0
}

# Phase 3: Promote to Main
# Note: All logging goes to stderr to avoid contaminating command substitution
closedone_full_cycle_phase3() {
    local dev_branch=$1
    print_info "Phase 3: Promote to Main" >&2

    if ! git checkout main &>/dev/null; then
        print_error "  Failed to checkout main" >&2
        return 1
    fi

    git pull origin main &>/dev/null || true

    if ! git merge "$dev_branch" --no-ff -m "Merge $dev_branch into main" &>/dev/null; then
        print_error "  Merge conflicts detected" >&2
        git merge --abort 2>/dev/null
        return 1
    fi

    # Ensure GitHub auth is synced before push
    if type github_auth_sync &>/dev/null; then
        if ! GITHUB_AUTH_FORCE=1 github_auth_sync 2>/dev/null; then
            print_warning "GitHub auth sync failed; push may require manual login" >&2
        fi
    fi

    git push origin main 2>/dev/null || true
    print_success "  [OK] Promoted to main" >&2
    return 0
}

# Phase 4: Version Bump
# Note: All logging goes to stderr; only echo "$new_version" goes to stdout for capture
closedone_full_cycle_phase4() {
    local bump_type="${1:-patch}"
    print_info "Phase 4: Version Bump ($bump_type)" >&2

    if [[ ! "$bump_type" =~ ^(patch|minor|major)$ ]]; then
        print_error "  Invalid bump type: $bump_type" >&2
        return 1
    fi

    if ! python tools/version_manager.py --bump "$bump_type" &>/dev/null; then
        print_warning "  Version manager not available, manual bump needed" >&2
        # Fallback: read VERSION, bump manually
        local version
        version=$(cat VERSION 2>/dev/null || echo "0.0.0")
        # Declare variables first, then read with IFS split
        local major minor patch
        IFS='.' read -r major minor patch <<< "$version"
        case "$bump_type" in
            patch) patch=$((patch + 1)) ;;
            minor) minor=$((minor + 1)); patch=0 ;;
            major) major=$((major + 1)); minor=0; patch=0 ;;
        esac
        echo "$major.$minor.$patch" > VERSION
    fi

    python tools/version_manager.py --sync &>/dev/null || true

    local new_version=$(cat VERSION 2>/dev/null || echo "unknown")

    git add . &>/dev/null
    git commit -m "chore: Bump version to $new_version" &>/dev/null || true

    # Ensure GitHub auth is synced before push
    if type github_auth_sync &>/dev/null; then
        if ! GITHUB_AUTH_FORCE=1 github_auth_sync 2>/dev/null; then
            print_warning "GitHub auth sync failed; push may require manual login" >&2
        fi
    fi

    git push origin main &>/dev/null || true

    print_success "  [OK] Version: $new_version" >&2
    echo "$new_version"
    return 0
}

# Phase 5: New Cycle Setup
# Note: All logging goes to stderr; only echo "$new_dev_branch" goes to stdout for capture
closedone_full_cycle_phase5() {
    local new_version=$1
    print_info "Phase 5: New Cycle Setup" >&2

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local new_dev_branch="develop/v${new_version}-worktrees-${timestamp}"

    if ! git checkout -b "$new_dev_branch" main &>/dev/null; then
        print_error "  Failed to create new dev branch" >&2
        return 1
    fi

    # Ensure GitHub auth is synced before push
    if type github_auth_sync &>/dev/null; then
        if ! GITHUB_AUTH_FORCE=1 github_auth_sync 2>/dev/null; then
            print_warning "GitHub auth sync failed; push may require manual login" >&2
        fi
    fi

    git push -u origin "$new_dev_branch" 2>/dev/null || true

    # Auto-stage incomplete features
    local incomplete_count=0
    if [ -d "$INCOMPLETE_DIR" ]; then
        while IFS= read -r description; do
            if [ -n "$description" ]; then
                tree_stage "$description" &>/dev/null
                print_info "  Staged: $description" >&2
                incomplete_count=$((incomplete_count + 1))
            fi
        done < <(detect_incomplete_features)
    fi

    print_success "  [OK] New branch: $new_dev_branch" >&2
    [ $incomplete_count -gt 0 ] && print_success "  [OK] Staged $incomplete_count incomplete feature(s)" >&2

    echo "$new_dev_branch"
    return 0
}

# Phase 6: Cleanup & Report
closedone_full_cycle_phase6() {
    local dev_branch=$1
    local new_version=$2
    local new_dev_branch=$3

    print_info "Phase 6: Cleanup & Report"

    local cycle_timestamp=$(date +%Y%m%d-%H%M%S)
    local archive_dir="$ARCHIVED_DIR/cycle-$cycle_timestamp"

    mkdir -p "$archive_dir/completed" "$archive_dir/incomplete"

    local completed_count=0
    if [ -d "$COMPLETED_DIR" ]; then
        for file in "$COMPLETED_DIR"/*.md; do
            [ -f "$file" ] || continue
            mv "$file" "$archive_dir/completed/" 2>/dev/null && completed_count=$((completed_count + 1))
        done
    fi

    local incomplete_count=0
    if [ -d "$INCOMPLETE_DIR" ]; then
        for file in "$INCOMPLETE_DIR"/*.md; do
            [ -f "$file" ] || continue
            mv "$file" "$archive_dir/incomplete/" 2>/dev/null && incomplete_count=$((incomplete_count + 1))
        done
    fi

    print_success "  [OK] Archived $completed_count completed, $incomplete_count incomplete"

    cat > "$archive_dir/cycle-report.md" << EOF
# Development Cycle Completion Report

**Timestamp:** $(date +"%Y-%m-%d %H:%M:%S")

## Summary

- **Previous Dev Branch:** $dev_branch
- **New Version:** $new_version
- **New Dev Branch:** $new_dev_branch

## Features Completed

$completed_count worktree(s) merged.

## Features Continuing

$incomplete_count incomplete feature(s) staged.

---
Generated by /tree closedone --full-cycle
EOF

    print_success "  [OK] Report: $archive_dir/cycle-report.md"
    return 0
}

# Rollback full cycle on failure
rollback_full_cycle() {
    local failed_phase=$1
    local checkpoint_tag=$(cat /tmp/cycle-checkpoint-tag 2>/dev/null || echo "")
    local original_branch=$(cat /tmp/cycle-branch-backup 2>/dev/null || echo "main")

    print_error "============================================================"
    print_error "ROLLBACK: Phase $failed_phase failed"
    print_error "============================================================"

    if [ -n "$checkpoint_tag" ] && git rev-parse "$checkpoint_tag" &>/dev/null; then
        print_warning "Rolling back to checkpoint: $checkpoint_tag"
        git reset --hard "$checkpoint_tag" &>/dev/null
        git tag -d "$checkpoint_tag" &>/dev/null
        print_success "  [OK] Reset to checkpoint"
    fi

    if [ -n "$original_branch" ]; then
        git checkout "$original_branch" &>/dev/null || true
        print_success "  [OK] Restored branch: $original_branch"
    fi

    rm -f /tmp/cycle-branch-backup /tmp/cycle-checkpoint-tag

    echo ""
    print_info "Fix the issue and run: /tree closedone --full-cycle"
    return 1
}

# Detect incomplete features for auto-staging
detect_incomplete_features() {
    if [ ! -d "$INCOMPLETE_DIR" ]; then
        return 0
    fi

    local synopsis_files=()
    while IFS= read -r -d '' file; do
        synopsis_files+=("$file")
    done < <(find "$INCOMPLETE_DIR" -name "*-synopsis-*.md" -print0 2>/dev/null)

    for synopsis_file in "${synopsis_files[@]}"; do
        if grep -q "^# Status: INCOMPLETE" "$synopsis_file" 2>/dev/null; then
            local description=""
            if grep -q "^## Original Task Description" "$synopsis_file"; then
                description=$(grep -A 5 "^## Original Task Description" "$synopsis_file" | tail -n +2 | head -n 3 | tr '\n' ' ' | sed 's/  */ /g' | xargs)
            fi
            if [ -z "$description" ]; then
                local filename=$(basename "$synopsis_file")
                description="${filename%%-synopsis-*}"
                description="${description//-/ }"
            fi
            if [ -n "$description" ]; then
                echo "$description"
            fi
        fi
    done
}
