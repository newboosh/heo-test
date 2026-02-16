#!/bin/bash
#
# Script: lib/setup.sh
# Purpose: Worktree setup and initialization functions
# Created: 2026-01-28
# Description: Creates worktree environment including commands, hooks, and context files

# Dependencies: lib/common.sh (print_* functions)
# Required variables: WORKSPACE_ROOT, SCRIPT_DIR, TREES_DIR

# Copy/symlink slash commands and scripts to worktree
# Usage: copy_slash_commands_to_worktree /path/to/worktree
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

# Install scope enforcement pre-commit hook in worktree
# Usage: install_scope_hook /path/to/worktree
install_scope_hook() {
    local worktree_path=$1

    # CRITICAL: In git worktrees, .git is a FILE (not a directory) that points to the actual git directory
    # We must use 'git rev-parse --git-dir' to get the real git directory path for the worktree
    local git_dir
    git_dir=$(cd "$worktree_path" && git rev-parse --git-dir 2>/dev/null)

    # Normalize git_dir to an absolute path (git rev-parse --git-dir can return
    # relative paths like ".git" for worktrees, which breaks subsequent checks)
    if [ -n "$git_dir" ] && [[ ! "$git_dir" = /* ]]; then
        git_dir="$worktree_path/$git_dir"
    fi

    if [ -z "$git_dir" ] || [ ! -d "$git_dir" ]; then
        print_warning "  Could not determine git directory for hooks, skipping hook installation"
        return 1
    fi

    # Create hooks directory in the worktree-specific git directory
    local hooks_dir="$git_dir/hooks"
    mkdir -p "$hooks_dir"

    # Create master pre-commit hook that runs all validation hooks
    cat > "$hooks_dir/pre-commit" << 'EOF'
#!/bin/bash

# Master Pre-Commit Hook
# Runs multiple validations in order of priority:
# 1. Worktree guard - prevents worktree-local files from being committed
# 2. Scope enforcement - ensures files match worktree scope
# 3. Librarian frontmatter - validates file metadata/headers

set -e
EXIT_CODE=0

# Find hook scripts in parent directory (same location as this git directory)
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$HOOKS_DIR/../../../" && pwd)"  # Go up to scripts/ directory
HOOKS_SCRIPTS_DIR="$(cd "$(dirname "$PARENT_DIR")/scripts" && pwd)"

echo ""
echo "Running pre-commit validations..."
echo ""

# 1. Worktree Guard Hook - HIGHEST PRIORITY
GUARD_HOOK="$HOOKS_SCRIPTS_DIR/worktree-commit-guard.sh"
if [ -f "$GUARD_HOOK" ]; then
    echo "-> Checking for worktree-local files..."
    if bash "$GUARD_HOOK"; then
        echo "[OK] Worktree guard passed"
    else
        echo "[FAIL] Worktree guard failed - worktree-local files detected"
        EXIT_CODE=1
    fi
else
    echo "[WARN] Worktree guard hook not found, skipping"
fi

echo ""

# 2. Scope Enforcement Hook
SCOPE_HOOK="$HOOKS_DIR/scope-enforcement-hook.sh"
if [ -f "$SCOPE_HOOK" ]; then
    echo "-> Checking scope boundaries..."
    if bash "$SCOPE_HOOK"; then
        echo "[OK] Scope validation passed"
    else
        echo "[FAIL] Scope validation failed"
        EXIT_CODE=1
    fi
else
    echo "[WARN] Scope enforcement hook not found, skipping"
fi

echo ""

# 3. Librarian Frontmatter Hook
FRONTMATTER_HOOK="$HOOKS_SCRIPTS_DIR/librarian-frontmatter-hook.sh"
if [ -f "$FRONTMATTER_HOOK" ]; then
    echo "-> Checking file frontmatter..."
    if bash "$FRONTMATTER_HOOK"; then
        echo "[OK] Frontmatter validation passed"
    else
        echo "[FAIL] Frontmatter validation failed"
        EXIT_CODE=1
    fi
else
    echo "[WARN] Frontmatter hook not found, skipping"
fi

echo ""

if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERROR] Pre-commit validations failed. Fix errors before committing."
    exit 1
fi

echo "[SUCCESS] All pre-commit validations passed!"
exit 0
EOF

    chmod +x "$hooks_dir/pre-commit"
}

# Generate VS Code tasks and auto-execute them
# Usage: generate_and_run_vscode_tasks
generate_and_run_vscode_tasks() {
    local pending_file="$TREES_DIR/.pending-terminals.txt"

    if [ ! -f "$pending_file" ]; then
        return 0
    fi

    print_info "Terminal initialization instructions:"
    echo ""
    echo "To launch Claude in each worktree, you can either:"
    echo ""
    echo "Option 1 - Manual launch (recommended for control):"
    echo "  - Open terminal for each worktree"
    echo "  - Run: cd <worktree-path> && bash .claude-init.sh"
    echo ""
    echo "Option 2 - Automatic launch:"

    local terminal_num=1
    while IFS= read -r worktree_path; do
        local wt_name=$(basename "$worktree_path")
        echo "  - Worktree $terminal_num: $wt_name"
        echo "    cd \"$worktree_path\" && bash .claude-init.sh"
        terminal_num=$((terminal_num + 1))
    done < "$pending_file"

    echo ""
    print_warning "Note: Automated terminal launch disabled to prevent unwanted editor tabs"
    print_info "The .claude-init.sh script in each worktree will launch Claude with task context"

    rm -f "$pending_file"
}

# Generate .claude-init.sh script for Claude auto-launch
# Usage: generate_init_script worktree_name description worktree_path
generate_init_script() {
    local worktree_name=$1
    local description=$2
    local worktree_path=$3
    local init_script="$worktree_path/.claude-init.sh"

    # Get plugin directory (parent of SCRIPT_DIR)
    local plugin_dir="$(cd "$SCRIPT_DIR/.." && pwd)"

    # Escape description for safe embedding in script
    # Order matters: escape backslashes first, then backticks, then quotes and dollar signs
    local escaped_desc="${description//\\/\\\\}"
    escaped_desc="${escaped_desc//\`/\\\`}"
    escaped_desc="${escaped_desc//\"/\\\"}"
    escaped_desc="${escaped_desc//\$/\\\$}"

    cat > "$init_script" << INITSCRIPT
#!/bin/bash
# Auto-generated Claude initialization script
# Launches Claude with heo plugin and auto-sends task description

WORKTREE_ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$WORKTREE_ROOT"

# Heo plugin location (embedded at build time)
HEO_PLUGIN_DIR="$plugin_dir"

# Task details (embedded at build time)
WORKTREE_NAME="$worktree_name"
TASK_DESCRIPTION="$escaped_desc"

# Display banner
echo ""
echo "================================================================"
echo "Worktree: \$WORKTREE_NAME"
echo "================================================================"
echo ""
echo "Task: \$TASK_DESCRIPTION"
echo ""
echo "================================================================"
echo ""
echo "Launching Claude Code with heo plugin..."
echo "   Plugin: \$HEO_PLUGIN_DIR"
echo "   Permissions: auto-approved (--dangerously-skip-permissions)"
echo "   First prompt: auto-sent with task description"
echo ""

# Check if Claude is available
if ! command -v claude &> /dev/null; then
    echo "Error: Claude Code not found in PATH"
    echo "Install: https://docs.anthropic.com/en/docs/claude-code"
    exec bash
    exit 1
fi

# Verify plugin exists
# Use array to safely handle paths with spaces
PLUGIN_ARGS=()
if [ -f "\$HEO_PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
    PLUGIN_ARGS=(--add-dir "\$HEO_PLUGIN_DIR")
else
    echo "Warning: Heo plugin not found at \$HEO_PLUGIN_DIR"
    echo "Launching without plugin..."
fi

# Build the initial prompt
INITIAL_PROMPT="I'm starting work on this worktree task:

## Task Description
\$TASK_DESCRIPTION

## Worktree Info
- **Name**: \$WORKTREE_NAME
- **Branch**: \$(git branch --show-current 2>/dev/null || echo 'unknown')

## Your Instructions
1. Read the CLAUDE.md and PURPOSE.md files to understand the full context
2. Review the codebase to understand what exists
3. Ask me 2-3 clarifying questions about:
   - Any ambiguous requirements
   - Technical decisions I should make
   - Integration points with existing code
   - Testing expectations

Please ask your clarifying questions now. I'll answer them before you start implementing."

# Launch Claude (use array expansion to handle spaces in paths)
exec claude "\${PLUGIN_ARGS[@]}" --dangerously-skip-permissions -p "\$INITIAL_PROMPT"
INITSCRIPT

    chmod +x "$init_script"
}

# Generate .claude-task-context.md file with full task description
# Usage: generate_task_context worktree_name description branch base_branch worktree_path
generate_task_context() {
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

    cat > "$worktree_path/.claude-task-context.md" << EOF
# Task Context for Claude Agent

## Worktree Information
- **Name**: $worktree_name
- **Branch**: $branch
- **Base Branch**: $base_branch
- **Created**: $(date +"%Y-%m-%d %H:%M:%S")

## Task Description

$escaped_desc

## Scope

This worktree is dedicated to implementing the feature described above. Focus on:
- Implementing the core functionality
- Writing tests for new features
- Updating documentation
- Following project coding standards

## Success Criteria

- [ ] Core functionality implemented
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Ready to merge to base branch

## Working in this Worktree

Slash commands are available!

After Claude starts, you can use:
- \`/tree close\` - Complete work and generate synopsis
- \`/tree status\` - Show worktree status
- \`/tree restore\` - Restore terminals (if needed)

## Notes

- This worktree is isolated from main development
- Commit frequently with descriptive messages
- Run tests before marking task complete
- Use \`/tree close\` when work is finished
EOF

    # Also create CLAUDE.md which Claude Code automatically reads
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
- \`.claude-task-context.md\` - Full task context
- \`.worktree-scope.json\` - Scope boundaries (auto-detected)

## When Complete

Run \`/tree close\` to:
1. Auto-commit all changes
2. Push branch to GitHub
3. Create a PR for review
EOF
}
