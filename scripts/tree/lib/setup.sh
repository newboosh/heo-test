#!/bin/bash
#
# Script: lib/setup.sh
# Purpose: Worktree setup and initialization functions
# Created: 2026-01-28
# Description: Creates worktree environment including commands, hooks, and context files

# Dependencies: lib/common.sh (print_* functions)
# Required variables: WORKSPACE_ROOT, SCRIPT_DIR, TREES_DIR

# Ensure plugin is listed in project settings for worktree discoverability
# Usage: ensure_enabled_plugins
#
# When Claude Code opens a session in a worktree,
# it needs enabledPlugins in .claude/settings.json to discover the plugin.
# This function ensures that entry exists in the target project's settings.
# All errors are non-fatal (returns 0 on any failure).
ensure_enabled_plugins() {
    local plugin_root
    plugin_root="$(cd "$SCRIPT_DIR/../.." && pwd)"

    # Read plugin identity from metadata files
    local plugin_json="$plugin_root/.claude-plugin/plugin.json"
    local marketplace_json="$plugin_root/.claude-plugin/marketplace.json"

    if [ ! -f "$plugin_json" ] || [ ! -f "$marketplace_json" ]; then
        print_warning "  Plugin metadata not found, skipping enabledPlugins check"
        return 0
    fi

    local plugin_name marketplace_name
    plugin_name=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['name'])" "$plugin_json" 2>/dev/null) || {
        print_warning "  Could not read plugin name from plugin.json"
        return 0
    }
    marketplace_name=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['name'])" "$marketplace_json" 2>/dev/null) || {
        print_warning "  Could not read marketplace name from marketplace.json"
        return 0
    }

    local plugin_id="${plugin_name}@${marketplace_name}"
    local settings_file="$WORKSPACE_ROOT/.claude/settings.json"

    # Ensure .claude directory exists
    mkdir -p "$WORKSPACE_ROOT/.claude"

    # Use python3 for safe JSON read/modify/write (jq may not be installed)
    local result
    result=$(python3 -c "
import json, sys, os

settings_file = sys.argv[1]
plugin_id = sys.argv[2]

settings = {}
if os.path.isfile(settings_file):
    try:
        with open(settings_file) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        settings = {}

enabled = settings.get('enabledPlugins', {})

if enabled.get(plugin_id) is True:
    print('EXISTS')
elif plugin_id in enabled and enabled[plugin_id] is False:
    print('DISABLED')
else:
    enabled[plugin_id] = True
    settings['enabledPlugins'] = enabled
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print('ADDED')
" "$settings_file" "$plugin_id" 2>/dev/null) || {
        print_warning "  Could not update enabledPlugins in settings.json"
        return 0
    }

    case "$result" in
        EXISTS)
            print_success "Plugin discoverable in worktrees (enabledPlugins already set)"
            ;;
        DISABLED)
            print_warning "Plugin explicitly disabled in settings.json (enabledPlugins: false) — not overwriting"
            ;;
        ADDED)
            print_success "Added ${plugin_id} to .claude/settings.json enabledPlugins"
            ;;
        *)
            print_warning "  Unexpected result from enabledPlugins check: $result"
            ;;
    esac

    return 0
}

# Set up .claude directory in worktree
# Usage: setup_worktree_claude_dir /path/to/worktree
#
# SAFETY: Only creates symlinks if target exists and worktree doesn't already have content.
# Never overwrites existing local directories - preserves user's customizations.
copy_slash_commands_to_worktree() {
    local worktree_path=$1
    local worktree_name
    worktree_name=$(basename "$worktree_path")

    # Create .claude directory
    mkdir -p "$worktree_path/.claude"

    # SYMLINK commands directory (so updates in main workspace propagate)
    # Only if: source exists AND destination doesn't exist (don't overwrite local content)
    if [ -d "$WORKSPACE_ROOT/.claude/commands" ]; then
        if [ -L "$worktree_path/.claude/commands" ]; then
            # It's already a symlink - check if it's broken
            if [ ! -e "$worktree_path/.claude/commands" ]; then
                # Broken symlink - remove and recreate
                rm -f "$worktree_path/.claude/commands"
                ln -sf "$WORKSPACE_ROOT/.claude/commands" "$worktree_path/.claude/commands"
            fi
            # Valid symlink exists - leave it alone
        elif [ ! -e "$worktree_path/.claude/commands" ]; then
            # Nothing exists - create symlink
            ln -sf "$WORKSPACE_ROOT/.claude/commands" "$worktree_path/.claude/commands"
        fi
        # If it's a real directory, don't touch it - preserve local content
    fi

    # SYMLINK scripts directory
    if [ -d "$WORKSPACE_ROOT/.claude/scripts" ]; then
        if [ -L "$worktree_path/.claude/scripts" ]; then
            if [ ! -e "$worktree_path/.claude/scripts" ]; then
                rm -f "$worktree_path/.claude/scripts"
                ln -sf "$WORKSPACE_ROOT/.claude/scripts" "$worktree_path/.claude/scripts"
            fi
        elif [ ! -e "$worktree_path/.claude/scripts" ]; then
            ln -sf "$WORKSPACE_ROOT/.claude/scripts" "$worktree_path/.claude/scripts"
        fi
    fi

    # SYMLINK settings.json if it exists
    if [ -f "$WORKSPACE_ROOT/.claude/settings.json" ]; then
        if [ -L "$worktree_path/.claude/settings.json" ]; then
            if [ ! -e "$worktree_path/.claude/settings.json" ]; then
                rm -f "$worktree_path/.claude/settings.json"
                ln -sf "$WORKSPACE_ROOT/.claude/settings.json" "$worktree_path/.claude/settings.json"
            fi
        elif [ ! -e "$worktree_path/.claude/settings.json" ]; then
            ln -sf "$WORKSPACE_ROOT/.claude/settings.json" "$worktree_path/.claude/settings.json"
        fi
    fi
}

# Generate CLAUDE.md for worktree (auto-read by Claude Code)
# Usage: generate_worktree_claude_md worktree_name description branch base_branch worktree_path
generate_worktree_claude_md() {
    local worktree_name=$1
    local description=$2
    local branch=$3
    local base_branch=$4
    local worktree_path=$5

    # Escape description to prevent code injection in heredocs
    # Must escape: backslashes, backticks, and dollar signs
    local escaped_desc="${description//\\/\\\\}"
    escaped_desc="${escaped_desc//\`/\\\`}"
    escaped_desc="${escaped_desc//\$/\\\$}"

    cat > "$worktree_path/CLAUDE.md" << EOF
# Worktree: ${worktree_name//-/ }

## YOUR TASK

$escaped_desc

## Context

You are working in a dedicated git worktree for this specific task.

- **Branch**: \`$branch\`
- **Base**: \`$base_branch\`
- **Worktree**: \`$worktree_name\`

## Important Guidelines

1. **Focus on this task only** - Don't work on unrelated features
2. **Use /tree commands**:
   - \`/tree close\` when done (commits, pushes, creates PR)
   - \`/tree status\` to check worktree state
3. **Commit frequently** with descriptive messages
4. **Run tests** before completing

## Files

- \`PURPOSE.md\` - Detailed task documentation

## When Complete

Run \`/tree close\` to:
1. Auto-commit all changes
2. Push branch to GitHub
3. Create a PR for review
EOF
}
