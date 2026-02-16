#!/bin/bash
#
# Script: commands/status.sh
# Purpose: Status and diagnostics commands for worktree system
# Created: 2026-01-28
# Description: Show worktree status, restore terminals, refresh session

# Dependencies: lib/common.sh (print_* functions), lib/setup.sh (generate_* functions)
# Required variables: TREES_DIR, STAGED_FEATURES_FILE, COMPLETED_DIR, SCRIPT_DIR

# /tree status
# Show worktree environment status
tree_status() {
    print_header "Worktree Environment Status"

    # Detect current location
    local current_dir=$(pwd)
    local current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")

    if [[ "$current_dir" == *"/.trees/"* ]]; then
        local worktree_name=$(basename "$current_dir")
        echo "Current Location: $current_dir"
        echo "Current Worktree: $worktree_name"
    else
        echo "Current Location: $WORKSPACE_ROOT (main)"
    fi

    echo "Current Branch: $current_branch"
    echo ""

    # List active worktrees
    print_info "Active Worktrees:"
    local worktree_count=0

    if [ -d "$TREES_DIR" ]; then
        for dir in "$TREES_DIR"/*/ ; do
            [ -d "$dir/.git" ] || [ -f "$dir/.git" ] || continue

            local name=$(basename "$dir")
            local branch=$(cd "$dir" && git branch --show-current 2>/dev/null || echo "unknown")

            echo "  [OK] $name ($branch)"
            worktree_count=$((worktree_count + 1))
        done
    fi

    if [ $worktree_count -eq 0 ]; then
        echo "  (none)"
    fi
    echo ""

    # Show staged features
    if [ -f "$STAGED_FEATURES_FILE" ]; then
        local staged_count=$(grep -vc '^#\|^$' "$STAGED_FEATURES_FILE" || true)
        if [ $staged_count -gt 0 ]; then
            print_info "Staged Features: $staged_count"
            echo "  Run /tree list to see details"
            echo ""
        fi
    fi

    # Show completed worktrees
    if [ -d "$COMPLETED_DIR" ]; then
        local completed_count=$(find "$COMPLETED_DIR" -name "*-synopsis-*.md" 2>/dev/null | wc -l | tr -d ' ')
        if [ $completed_count -gt 0 ]; then
            print_info "Completed Worktrees: $completed_count"
            echo "  Run /tree closedone to merge and cleanup"
            echo ""
        fi
    fi

    # Show build history
    if [ -d "$TREES_DIR/.build-history" ]; then
        local recent_build=$(ls -t "$TREES_DIR/.build-history" 2>/dev/null | head -1)
        if [ -n "$recent_build" ]; then
            print_info "Most Recent Build:"
            echo "  ${recent_build%.txt}"
            echo ""
        fi
    fi

    echo "Actions:"
    echo "  - /tree stage [description] - Stage new feature"
    echo "  - /tree build - Create worktrees from staged features"
    echo "  - /tree close - Complete current worktree"
    echo "  - /tree closedone - Merge completed worktrees"
}

# /tree restore
# Restore terminals for worktrees without active shells
tree_restore() {
    print_header "Reconnecting Worktree Terminals"

    # Find all existing worktrees
    local worktrees=()
    if [ -d "$TREES_DIR" ]; then
        for dir in "$TREES_DIR"/*/ ; do
            if [ -d "$dir/.git" ] || [ -f "$dir/.git" ]; then
                local name=$(basename "$dir")
                worktrees+=("$name|||$dir")
            fi
        done
    fi

    if [ ${#worktrees[@]} -eq 0 ]; then
        print_warning "No worktrees found"
        echo "Create worktrees first: /tree build"
        return 0
    fi

    print_info "Found ${#worktrees[@]} worktree(s)"
    echo ""

    # Filter worktrees that need terminals
    local needs_terminal=()
    for worktree_info in "${worktrees[@]}"; do
        local name="${worktree_info%%|||*}"
        local path="${worktree_info#*|||}"

        # Check if init script exists
        if [ -f "$path/.claude-init.sh" ]; then
            print_warning "  [!] $name - Needs terminal"
            needs_terminal+=("$path")
        else
            print_warning "  [!] $name - Missing init script, regenerating..."
            # Regenerate init script
            local desc=$(head -1 "$path/PURPOSE.md" 2>/dev/null | sed 's/# Purpose: //' || echo "Worktree task")
            generate_init_script "$name" "$desc" "$path"
            needs_terminal+=("$path")
        fi
    done

    echo ""

    if [ ${#needs_terminal[@]} -eq 0 ]; then
        print_success "All worktrees have init scripts"
        return 0
    fi

    # Create pending terminals file
    rm -f "$TREES_DIR/.pending-terminals.txt"
    for path in "${needs_terminal[@]}"; do
        echo "$path" >> "$TREES_DIR/.pending-terminals.txt"
    done

    print_header "Launching Terminals"
    generate_and_run_vscode_tasks

    print_success "Terminal reconnection complete"
}

# /tree refresh
# Session guidance for slash command loading
tree_refresh() {
    print_header "Slash Command Session Check"

    local current_dir=$(pwd)
    local in_worktree=false

    # Detect if we're in a worktree
    if [[ "$current_dir" == *"/.trees/"* ]]; then
        in_worktree=true
        local worktree_name=$(basename "$current_dir")
    fi

    echo "Current Location:"
    echo "   $current_dir"
    echo ""

    if [ "$in_worktree" = true ]; then
        echo "Worktree Detected: $worktree_name"
        echo ""
    fi

    # Check if slash command files exist
    echo "Checking Slash Command Files:"

    local commands_found=0
    local commands_missing=0

    for cmd in tree task; do
        if [ -f ".claude/commands/$cmd.md" ]; then
            print_success "/$cmd command file exists"
            commands_found=$((commands_found + 1))
        else
            print_error "/$cmd command file MISSING"
            commands_missing=$((commands_missing + 1))
        fi
    done

    echo ""

    if [ $commands_missing -gt 0 ]; then
        print_error "Missing command files detected!"
        echo ""
        echo "This worktree may be on an older commit. Consider:"
        echo "  1. Merge latest changes from main/develop"
        echo "  2. Cherry-pick the slash command commits"
        echo ""
        return 1
    fi

    # Provide session reload guidance
    print_header "Claude Code CLI Session Guidance"

    print_info "Known Issue: Claude Code doesn't always reload slash commands"
    echo "   when switching between worktrees mid-session."
    echo ""

    if [ "$in_worktree" = true ]; then
        print_warning "You're in a worktree. If /tree or /task don't work:"
        echo ""
        echo "  Quick Fix (Recommended):"
        echo "    Use direct command: bash \"$SCRIPT_DIR/tree.sh\" <command>"
        echo "    Example: bash \"$SCRIPT_DIR/tree.sh\" status"
        echo ""
        echo "  Permanent Fix:"
        echo "    Restart Claude Code CLI session"
        echo "    Start new session FROM this worktree directory"
        echo "    CLI will rescan commands on session start"
    else
        print_success "You're in main workspace - slash commands should work"
        echo ""
        echo "  If commands still don't work:"
        echo "    Restart Claude Code CLI session"
        echo "    Verify the heo plugin is installed"
    fi

    echo ""
    print_header "Workaround Commands"
    echo ""
    echo "Instead of /tree commands, use:"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" stage [description]"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" list"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" build"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" close"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" closedone"
    echo "  bash \"$SCRIPT_DIR/tree.sh\" status"
    echo ""

    print_info "All functionality works identically via direct script calls"
}
