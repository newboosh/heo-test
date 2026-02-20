#!/bin/bash
#
# Script: commands/sync.sh
# Purpose: Sync worktrees from source/main via rebase
# Usage:
#   /tree sync          - Sync current worktree only (run from inside a worktree)
#   /tree sync --all    - Sync all worktrees (run from repo root)
#
# Strategy:
#   1. Pull source/main into the main repo
#   2. For each target worktree:
#      a. Detect and report untracked files (stashed for review)
#      b. Stash all changes including untracked
#      c. Rebase branch onto main
#      d. Pop stash so changes can be reviewed against post-rebase state
#      e. Report result
#
# Detached HEAD worktrees are reported but skipped (cannot rebase without a branch).

# Dependencies: lib/common.sh (print_* functions)
# Required variables: WORKSPACE_ROOT, TREES_DIR

# Detect which remote is available (prefer 'source', fall back to 'origin')
_detect_remote() {
    if git -C "$WORKSPACE_ROOT" remote get-url source &>/dev/null; then
        echo "source"
    elif git -C "$WORKSPACE_ROOT" remote get-url origin &>/dev/null; then
        echo "origin"
    else
        echo ""
    fi
}

# Pull source/main into the main repo. Updates the local main ref.
_pull_main() {
    local remote="$1"

    print_info "Fetching $remote/main..."
    if ! git -C "$WORKSPACE_ROOT" fetch "$remote" main 2>&1; then
        print_error "Failed to fetch $remote/main — check network and credentials."
        return 1
    fi

    # The main worktree may have 'main' checked out; update it safely
    local current_branch
    current_branch=$(git -C "$WORKSPACE_ROOT" branch --show-current 2>/dev/null || echo "")

    if [ "$current_branch" = "main" ]; then
        if ! git -C "$WORKSPACE_ROOT" merge --ff-only "$remote/main" 2>&1; then
            print_warning "Could not fast-forward main (local divergence). Fetch only."
        else
            print_success "main updated to $(git -C "$WORKSPACE_ROOT" rev-parse --short HEAD)"
        fi
    else
        # Update the local main ref without checking it out
        git -C "$WORKSPACE_ROOT" update-ref refs/heads/main refs/remotes/"$remote"/main 2>/dev/null || true
        print_success "main ref updated to $(git -C "$WORKSPACE_ROOT" rev-parse --short refs/heads/main 2>/dev/null)"
    fi
}

# Report untracked files in a worktree (informational only — they will be stashed)
_handle_untracked() {
    local wt_path="$1"

    local untracked
    untracked=$(git -C "$wt_path" ls-files --others --exclude-standard 2>/dev/null)

    [ -z "$untracked" ] && return 0

    print_info "Untracked files in $(basename "$wt_path") (will be stashed for review):"
    echo "$untracked" | while IFS= read -r f; do
        echo "    $f"
    done

    return 0
}

# Stash all changes (tracked and untracked). Echoes stash message if stashed, empty string if nothing to stash.
# Untracked files are included so they can be reviewed against post-rebase state when the stash is popped.
_stash_changes() {
    local wt_path="$1"

    local dirty
    dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null)
    [ -z "$dirty" ] && echo "" && return 0

    local stash_msg="tree-sync: pre-rebase stash $(date +%Y%m%d-%H%M%S)"
    git -C "$wt_path" stash push --include-untracked -m "$stash_msg" --quiet 2>/dev/null || true

    # Verify a stash was actually created (git exits 0 even when nothing was stashed)
    if git -C "$wt_path" stash list 2>/dev/null | grep -qF "$stash_msg"; then
        echo "$stash_msg"
    else
        echo ""
    fi
}

# Rebase a single worktree branch onto main. Returns exit code of rebase.
_rebase_worktree() {
    local wt_path="$1"
    local wt_name
    wt_name="$(basename "$wt_path")"

    local branch
    branch=$(git -C "$wt_path" branch --show-current 2>/dev/null || echo "")

    if [ -z "$branch" ]; then
        print_warning "  $wt_name: Detached HEAD — skipping (no branch to rebase)."
        print_info "    Tip: run 'git -C $wt_path checkout -b <name>' to attach a branch."
        return 0
    fi

    local ahead
    ahead=$(git -C "$wt_path" rev-list --count main..HEAD 2>/dev/null || echo "0")

    if [ "$ahead" = "0" ]; then
        print_success "  $wt_name [$branch]: Already up to date."
        return 0
    fi

    print_info "  $wt_name [$branch]: Rebasing $ahead commit(s) onto main..."
    if git -C "$wt_path" rebase main --quiet 2>&1; then
        print_success "  $wt_name [$branch]: Rebased successfully."
        return 0
    else
        print_error "  $wt_name [$branch]: Rebase FAILED — conflicts need manual resolution."
        print_info "    To fix: cd $wt_path && git rebase --abort  (to cancel)"
        print_info "            cd $wt_path && git rebase --continue (after resolving)"
        return 1
    fi
}

# Sync a single worktree (path)
_sync_one() {
    local wt_path="$1"
    local wt_name
    wt_name="$(basename "$wt_path")"

    echo ""
    print_info "── $wt_name ──"

    _handle_untracked "$wt_path"

    local stash_msg
    stash_msg=$(_stash_changes "$wt_path")

    if [ -n "$stash_msg" ]; then
        print_info "  Stashed uncommitted changes."
    fi

    local rebase_ok=0
    _rebase_worktree "$wt_path" || rebase_ok=1

    if [ -n "$stash_msg" ]; then
        if [ $rebase_ok -eq 0 ]; then
            # Rebase succeeded — restore stash
            if git -C "$wt_path" stash pop --quiet 2>/dev/null; then
                print_success "  Stash restored."
            else
                print_warning "  Could not auto-restore stash — run 'git stash pop' manually in $wt_name."
            fi
        else
            # Rebase failed — leave stash intact to avoid polluting a conflicted tree
            print_warning "  Stash preserved (rebase failed). After resolving conflicts, run:"
            print_info "    cd $wt_path && git stash pop"
        fi
    fi

    return $rebase_ok
}

# ─── Public Command Functions ──────────────────────────────────────────────────

# /tree sync  (single worktree mode — run from inside a worktree)
tree_sync() {
    local all_mode="false"

    while [ $# -gt 0 ]; do
        case "$1" in
            --all) all_mode="true" ;;
            *) print_error "Unknown option: $1"; return 1 ;;
        esac
        shift
    done

    print_header "Worktree Sync from source/main"

    local remote
    remote=$(_detect_remote)
    if [ -z "$remote" ]; then
        print_error "No usable remote found. Expected 'source' or 'origin'."
        return 1
    fi

    # Pull main first
    _pull_main "$remote" || return 1

    if [ "$all_mode" = "true" ]; then
        # ── ALL MODE: sync every worktree from root ──────────────────────────
        local current_dir
        current_dir=$(pwd)

        if [[ "$current_dir" == "$TREES_DIR"* ]]; then
            print_error "--all must be run from the repo root, not inside a worktree."
            return 1
        fi

        if [ ! -d "$TREES_DIR" ]; then
            print_warning "No .trees/ directory found. Nothing to sync."
            return 0
        fi

        local failed=0
        local synced=0

        for wt_path in "$TREES_DIR"/*/; do
            # Skip hidden/meta dirs like .completed, .archived
            local wt_name="$(basename "$wt_path")"
            [[ "$wt_name" == .* ]] && continue
            [ -d "$wt_path/.git" ] || [ -f "$wt_path/.git" ] || continue

            _sync_one "$wt_path" || failed=$((failed + 1))
            synced=$((synced + 1))
        done

        echo ""
        if [ $synced -eq 0 ]; then
            print_warning "No worktrees found to sync."
        elif [ $failed -eq 0 ]; then
            print_success "All $synced worktree(s) synced successfully."
        else
            print_warning "$failed of $synced worktree(s) had rebase conflicts — resolve manually."
        fi

    else
        # ── SINGLE MODE: sync current worktree only ──────────────────────────
        local current_dir
        current_dir=$(pwd)

        if [[ "$current_dir" != "$TREES_DIR"* ]]; then
            print_error "You are not inside a worktree."
            echo ""
            echo "  From root, use:  /tree sync --all"
            echo "  From a worktree: /tree sync"
            return 1
        fi

        _sync_one "$current_dir"
        local result=$?
        echo ""
        if [ $result -eq 0 ]; then
            print_success "Sync complete."
        else
            print_warning "Sync completed with errors — see above."
        fi
        return $result
    fi
}
