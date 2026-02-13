#!/bin/bash
#
# Script: commands/build.sh
# Purpose: Worktree build command
# Created: 2026-01-28
# Description: Create worktrees from staged features with scope detection

# Dependencies: lib/common.sh, lib/git-safety.sh, lib/validation.sh, lib/state.sh, lib/setup.sh, scope-detector.sh
# Required variables: TREES_DIR, STAGED_FEATURES_FILE, WORKSPACE_ROOT, BUILD_STATE_FILE, SCRIPT_DIR

# /tree build [options]
# Create worktrees from staged features
tree_build() {
    # Parse options
    local confirm_mode=false
    local verbose_mode="${TREE_VERBOSE:-false}"
    local resume_mode=false
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --confirm)
                confirm_mode=true
                shift
                ;;
            --verbose|-v)
                export TREE_VERBOSE=true
                verbose_mode=true
                shift
                ;;
            --resume)
                resume_mode=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: /tree build [--confirm] [--verbose] [--resume] [--dry-run]"
                return 1
                ;;
        esac
    done

    # Handle resume mode
    if [ "$resume_mode" = "true" ]; then
        if load_build_state; then
            local saved_timestamp=$(get_build_state_value "timestamp")
            local saved_branch=$(get_build_state_value "dev_branch")
            local saved_total=$(get_build_state_value "total_features")
            local saved_failed=$(get_build_state_value "failed_worktree")

            print_header "Found Incomplete Build"
            echo "Timestamp: ${saved_timestamp}"
            echo "Dev Branch: ${saved_branch}"
            if [ -n "$saved_failed" ] && [ "$saved_failed" != "null" ]; then
                echo "Failed at: ${saved_failed}"
            fi
            echo ""
            print_info "Resuming from failure point..."
        else
            print_warning "No incomplete build found. Running normal build instead."
            resume_mode=false
        fi
    fi

    if [ ! -f "$STAGED_FEATURES_FILE" ]; then
        print_error "No features staged"
        echo "Use: /tree stage [description] to stage features first"
        return 1
    fi

    # Read staged features
    local features=()

    if [ "$resume_mode" = "true" ] && [ -f "$BUILD_STATE_FILE" ]; then
        while IFS= read -r feature; do
            features+=("$feature")
        done < <(get_build_state_remaining)
    else
        # Note: IFS='|||' splits on single '|' chars, so parse the full line instead
        while IFS= read -r line; do
            [[ "$line" =~ ^#.*$ ]] && continue
            [ -z "$line" ] && continue
            local name="${line%%|||*}"
            [ -z "$name" ] && continue
            features+=("$line")
        done < "$STAGED_FEATURES_FILE"
    fi

    if [ ${#features[@]} -eq 0 ]; then
        print_error "No features to build"
        return 1
    fi

    if [ "$dry_run" = true ]; then
        print_header "[DRY RUN] Building ${#features[@]} Worktree(s)"
        echo "This is a preview - no changes will be made."
        echo ""
    else
        print_header "Building ${#features[@]} Worktree(s)"
    fi

    if [ "$verbose_mode" = "true" ]; then
        print_info "Verbose mode enabled"
        echo ""
    fi

    # PRE-FLIGHT VALIDATION
    echo "============================================================"
    echo "PRE-FLIGHT CHECKS"
    echo "============================================================"
    echo ""

    if [ "$dry_run" = true ]; then
        print_info "[DRY RUN] Would check for stale locks"
        print_info "[DRY RUN] Would prune stale worktree references"
        print_info "[DRY RUN] Would cleanup orphaned directories"
    else
        if ! check_git_locks; then
            print_error "Pre-flight check failed: git locks detected"
            return 1
        fi
        echo ""

        print_info "Pruning stale worktree references..."
        if git worktree prune -v 2>&1 | grep -q "Removing"; then
            print_success "Pruned stale worktree references"
        else
            print_success "No stale references to prune"
        fi
        echo ""

        cleanup_orphaned_worktrees
    fi
    echo ""

    echo "============================================================"
    echo ""

    # Get or reuse development branch
    local dev_branch
    if [ "$resume_mode" = "true" ] && [ -f "$BUILD_STATE_FILE" ]; then
        dev_branch=$(get_build_state_value "dev_branch")
        print_info "Resuming with dev branch: $dev_branch"
    else
        local version=$(cat "$WORKSPACE_ROOT/VERSION" 2>/dev/null || echo "0.0.0")
        local timestamp=$(date +%Y%m%d-%H%M%S)
        dev_branch="develop/v${version}-worktrees-${timestamp}"
    fi

    echo "Features to build:"
    for i in "${!features[@]}"; do
        local feature="${features[$i]}"
        local name="${feature%%|||*}"
        echo "  $((i+1)). $name"
    done
    echo ""
    echo "Development Branch: $dev_branch"
    echo ""

    if [ "$dry_run" = true ]; then
        echo "============================================================"
        echo "DRY RUN PREVIEW - Worktrees that would be created:"
        echo "============================================================"
        echo ""

        for i in "${!features[@]}"; do
            local feature="${features[$i]}"
            local name="${feature%%|||*}"
            local desc="${feature#*|||}"
            local num=$((i+1))
            local task_num=$(printf "%02d" $num)

            local sanitized_desc=$(echo "$desc" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//')
            local worktree_name="${task_num}-${sanitized_desc}"
            local branch="${task_num}-${sanitized_desc}"
            local worktree_path="$TREES_DIR/$worktree_name"

            echo "[$num] $worktree_name"
            echo "    Branch: $branch"
            echo "    Path: $worktree_path"
            echo "    Description: ${desc:0:60}..."
            echo ""
        done

        echo "[+1] librarian"
        echo "    Branch: task/00-librarian"
        echo "    Path: $TREES_DIR/librarian"
        echo "    Description: Documentation, tooling, and project organization"
        echo ""

        echo "============================================================"
        print_info "Dry run complete. Run without --dry-run to create worktrees."
        return 0
    fi

    # Create development branch
    if ! git rev-parse --verify "$dev_branch" &>/dev/null; then
        wait_for_git_lock || return 1
        # Capture output and exit code separately to avoid masking errors
        local checkout_output
        local checkout_exit
        checkout_output=$(safe_git checkout -b "$dev_branch" 2>&1)
        checkout_exit=$?
        if [ $checkout_exit -eq 0 ]; then
            print_success "Created development branch: $dev_branch"
        elif echo "$checkout_output" | grep -q "already exists"; then
            print_info "Development branch already exists: $dev_branch (reusing)"
            safe_git checkout "$dev_branch" &>/dev/null
        else
            print_error "Failed to create development branch: $dev_branch"
            echo "$checkout_output" >&2
            return 1
        fi
    else
        print_info "Development branch already exists: $dev_branch (reusing)"
        safe_git checkout "$dev_branch" &>/dev/null
    fi

    # Track created worktrees for rollback
    local created_worktrees=()
    local success_count=0
    local failed_count=0
    local build_start=$(date +%s)

    # Save initial build state
    if [ "$resume_mode" != "true" ]; then
        # Use Python for safe JSON encoding to handle special characters
        local all_features_json
        all_features_json=$(printf '%s\n' "${features[@]}" | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
        save_build_state "$dev_branch" "${#features[@]}" "[]" "" "$all_features_json"
    fi

    for i in "${!features[@]}"; do
        local feature="${features[$i]}"
        local name="${feature%%|||*}"
        local desc="${feature#*|||}"
        local num=$((i+1))
        local task_num=$(printf "%02d" $num)

        local sanitized_desc=$(echo "$desc" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//')
        local worktree_name="${task_num}-${sanitized_desc}"
        local branch="${task_num}-${sanitized_desc}"
        local worktree_path="$TREES_DIR/$worktree_name"
        local worktree_start=$(date +%s)

        echo "[$num/${#features[@]}] Creating: $worktree_name"

        # Confirm mode
        if [ "$confirm_mode" = true ]; then
            if ! confirm_prompt "  Create this worktree?" "y"; then
                print_info "  Skipped"
                continue
            fi
        fi

        # Pre-flight validation
        if ! validate_and_cleanup_worktree_path "$worktree_path" "$branch"; then
            print_error "  [FAIL] Pre-flight validation failed"
            failed_count=$((failed_count + 1))

            # Save failure state (use Python for safe JSON encoding)
            local completed_names_json
            completed_names_json=$(for wt in "${created_worktrees[@]}"; do basename "${wt%%|||*}"; done | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
            local remaining_features_json
            remaining_features_json=$(printf '%s\n' "${features[@]:$i}" | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
            save_build_state "$dev_branch" "${#features[@]}" "$completed_names_json" "$name" "$remaining_features_json"
            print_info "To resume from this point, run: /tree build --resume"

            if [ ${#created_worktrees[@]} -gt 0 ]; then
                echo ""
                rollback_build "${created_worktrees[@]}"
            fi
            return 1
        fi

        # Create worktree
        wait_for_git_lock || {
            print_error "  [FAIL] Failed to acquire git lock"
            failed_count=$((failed_count + 1))
            if [ ${#created_worktrees[@]} -gt 0 ]; then
                rollback_build "${created_worktrees[@]}"
            fi
            return 1
        }

        if ! safe_git worktree add -b "$branch" "$worktree_path" "$dev_branch" &>/dev/null; then
            print_error "  [FAIL] Failed to create worktree: $branch"
            failed_count=$((failed_count + 1))

            local completed_names_json
            completed_names_json=$(for wt in "${created_worktrees[@]}"; do basename "${wt%%|||*}"; done | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
            local remaining_features_json
            remaining_features_json=$(printf '%s\n' "${features[@]:$i}" | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
            save_build_state "$dev_branch" "${#features[@]}" "$completed_names_json" "$name" "$remaining_features_json"
            print_info "To resume from this point, run: /tree build --resume"

            if [ ${#created_worktrees[@]} -gt 0 ]; then
                rollback_build "${created_worktrees[@]}"
            fi
            return 1
        fi

        created_worktrees+=("$worktree_path|||$branch")

        # Generate scope manifest
        if type detect_scope_from_description &>/dev/null; then
            local scope_manifest=$(detect_scope_from_description "$desc" "$name")
            echo "$scope_manifest" > "$worktree_path/.worktree-scope.json"
        else
            echo '{"scope":{"include":["**/*"],"exclude":[]},"enforcement":"soft"}' > "$worktree_path/.worktree-scope.json"
        fi

        # Create PURPOSE.md
        local scope_patterns="- **/*"
        if [ -f "$worktree_path/.worktree-scope.json" ] && command -v python3 &>/dev/null; then
            scope_patterns=$(cat "$worktree_path/.worktree-scope.json" | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join(['- ' + p for p in data.get('scope',{}).get('include',['**/*'])[:5]]))" 2>/dev/null || echo "- **/*")
        fi

        cat > "$worktree_path/PURPOSE.md" << EOF
# Purpose: ${name//-/ }

**Worktree:** $name
**Branch:** $branch
**Base Branch:** $dev_branch
**Created:** $(date +"%Y-%m-%d %H:%M:%S")

## Objective

$desc

## Scope

**Automatically detected scope patterns:**

$scope_patterns

**Full scope details:** See \`.worktree-scope.json\`

**Enforcement:** Soft (warnings only)

## Out of Scope

Files outside the detected patterns will generate warnings but are not blocked.
For hard enforcement, see \`.worktree-scope.json\` and modify \`enforcement\` setting.

## Slash Command Usage

If \`/tree\` or \`/task\` commands don't work in this worktree:

### Quick Fix:
\`\`\`bash
bash "$SCRIPT_DIR/tree.sh" <command>
\`\`\`

### Permanent Fix:
Restart Claude Code CLI session from this directory.

## Success Criteria

- [ ] All functionality implemented
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Ready to merge

## Notes

[Add implementation notes, decisions, or concerns here]
EOF

        # Generate context files and setup
        generate_task_context "$name" "$desc" "$branch" "$dev_branch" "$worktree_path"
        copy_slash_commands_to_worktree "$worktree_path"
        install_scope_hook "$worktree_path"
        generate_init_script "$name" "$desc" "$worktree_path"

        local worktree_end=$(date +%s)
        local worktree_duration=$((worktree_end - worktree_start))
        print_success "  [OK] Created in ${worktree_duration}s"
        success_count=$((success_count + 1))

        # Update build state (use Python for safe JSON encoding)
        local completed_names_json
        completed_names_json=$(for wt in "${created_worktrees[@]}"; do basename "${wt%%|||*}"; done | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
        local remaining_features_json
        remaining_features_json=$(printf '%s\n' "${features[@]:$((i+1))}" | python3 -c 'import sys, json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
        save_build_state "$dev_branch" "${#features[@]}" "$completed_names_json" "" "$remaining_features_json"

        echo "$worktree_path" >> "$TREES_DIR/.pending-terminals.txt"
    done

    # Create librarian worktree
    if [ $success_count -gt 0 ]; then
        echo ""
        print_header "Creating Librarian Worktree"

        local librarian_name="librarian"
        local librarian_branch="task/00-librarian"
        local librarian_path="$TREES_DIR/$librarian_name"

        wait_for_git_lock || true
        if safe_git worktree add -b "$librarian_branch" "$librarian_path" "$dev_branch" &>/dev/null; then
            # Generate librarian scope
            if type calculate_librarian_scope &>/dev/null; then
                local scope_files=()
                for worktree_dir in "$TREES_DIR"/*; do
                    if [ -d "$worktree_dir" ] && [ -f "$worktree_dir/.worktree-scope.json" ]; then
                        scope_files+=("$worktree_dir/.worktree-scope.json")
                    fi
                done
                local librarian_scope=$(calculate_librarian_scope "${scope_files[@]}")
                echo "$librarian_scope" > "$librarian_path/.worktree-scope.json"
            else
                echo '{"scope":{"include":["docs/**","*.md","scripts/**",".claude/**"],"exclude":[]},"enforcement":"soft"}' > "$librarian_path/.worktree-scope.json"
            fi

            cat > "$librarian_path/PURPOSE.md" << EOF
# Purpose: Librarian - Documentation & Tooling

**Worktree:** $librarian_name
**Branch:** $librarian_branch
**Base Branch:** $dev_branch
**Created:** $(date +"%Y-%m-%d %H:%M:%S")
**Type:** Meta-worktree (Documentation, tooling, project organization)

## Objective

Manage documentation, tooling, and project organization files that are not specific to any feature worktree.

## Scope

This worktree can work on files NOT claimed by feature worktrees, including:
- Documentation files (docs/**, *.md)
- Tooling and scripts (.claude/**, tools/**, scripts/**)
- Configuration files (*.toml, *.yaml, *.json)
- GitHub workflows (.github/**)

## Success Criteria

- [ ] Documentation updated and consistent
- [ ] Tooling improvements implemented
- [ ] Project organization enhanced

## Notes

The librarian worktree has inverse scope - it automatically excludes all files that feature worktrees are working on.
EOF

            copy_slash_commands_to_worktree "$librarian_path"
            install_scope_hook "$librarian_path"
            generate_task_context "$librarian_name" "Documentation, tooling, and project organization" "$librarian_branch" "$dev_branch" "$librarian_path"
            generate_init_script "$librarian_name" "Manage documentation and tooling" "$librarian_path"

            print_success "  [OK] Created librarian worktree"
            echo "$librarian_path" >> "$TREES_DIR/.pending-terminals.txt"
            success_count=$((success_count + 1))
        else
            print_warning "  [!] Failed to create librarian worktree (non-critical)"
        fi
    fi

    local build_end=$(date +%s)
    local total_duration=$((build_end - build_start))

    # Archive staging file
    local build_history_dir="$TREES_DIR/.build-history"
    mkdir -p "$build_history_dir"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    mv "$STAGED_FEATURES_FILE" "$build_history_dir/${timestamp}.txt" 2>/dev/null || true

    echo ""
    echo "============================================================"
    echo "BUILD SUMMARY"
    echo ""
    echo "Development Branch: $dev_branch"
    echo "Worktrees Created: $success_count"
    echo "Failed: $failed_count"
    echo "Total Time: ${total_duration}s"
    echo ""
    echo "Worktree Location: $TREES_DIR/"
    echo "============================================================"

    if [ $success_count -gt 0 ]; then
        echo ""
        print_header "Terminal Launch Instructions"
        generate_and_run_vscode_tasks

        echo ""
        print_success "All worktrees ready!"
        echo ""
        print_info "Next Steps:"
        echo "  1. Open terminal for each worktree"
        echo "  2. Navigate: cd <worktree-path>"
        echo "  3. Launch Claude: bash .claude-init.sh"
        echo "  4. When done: /tree close"
        echo "  5. Merge all: /tree closedone"

        clear_build_state

        echo ""
        tree_scope_conflicts 2>/dev/null || true
    fi
}
