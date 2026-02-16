#!/bin/bash
# Heo Plugin Shell Alias
# Source this file in your .bashrc or .zshrc:
#   source /path/to/heo/scripts/shell-alias.sh

# Detect plugin directory (where this script lives)
HEO_PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# Main alias function
claude-heo() {
    local args=()
    local skip_permissions=false
    local prompt=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -y|--yes)
                skip_permissions=true
                shift
                ;;
            -p|--prompt)
                prompt="$2"
                shift 2
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    # Build claude command
    local cmd=(claude)

    # Add plugin
    cmd+=(--add-dir "$HEO_PLUGIN_DIR")

    # Add skip permissions if requested
    if $skip_permissions; then
        cmd+=(--dangerously-skip-permissions)
    fi

    # Add prompt if provided
    if [[ -n "$prompt" ]]; then
        cmd+=(-p "$prompt")
    fi

    # Add remaining args
    cmd+=("${args[@]}")

    # Execute
    "${cmd[@]}"
}

# Short alias
alias ch='claude-heo'

# Worktree-aware variant (auto-loads task context)
claude-heo-tree() {
    local worktree_root
    worktree_root=$(git rev-parse --show-toplevel 2>/dev/null)

    if [[ -z "$worktree_root" ]]; then
        echo "Error: Not in a git repository"
        return 1
    fi

    local context_file="$worktree_root/.claude-task-context.md"
    local purpose_file="$worktree_root/.claude-purpose-context.md"
    local worktree_name
    worktree_name=$(basename "$worktree_root")

    # Set terminal title
    echo -ne "\033]0;claude $worktree_name\007"

    # Build system prompt from context files
    local system_prompt=""
    if [[ -f "$context_file" ]]; then
        system_prompt="You are working in a git worktree. Read .claude-task-context.md for full details.

IMPORTANT: Ask 1-3 clarifying questions before starting implementation."
    elif [[ -f "$purpose_file" ]]; then
        system_prompt="You are working in a git worktree. Read .claude-purpose-context.md for full details.

IMPORTANT: Focus on this worktree's specific purpose."
    fi

    # Launch with context
    if [[ -n "$system_prompt" ]]; then
        claude-heo --yes --append-system-prompt "$system_prompt" "$@"
    else
        claude-heo "$@"
    fi
}

# Short alias for tree variant
alias cht='claude-heo-tree'

# Print help on first source
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Heo Plugin Aliases"
    echo "====================="
    echo ""
    echo "Usage:"
    echo "  claude-heo [options]    Launch Claude with heo plugin"
    echo "  ch                         Short alias for claude-heo"
    echo "  claude-heo-tree         Launch in worktree with task context"
    echo "  cht                        Short alias for claude-heo-tree"
    echo ""
    echo "Options:"
    echo "  -y, --yes                  Skip permission prompts"
    echo "  -p, --prompt <text>        Start with initial prompt"
    echo ""
    echo "Installation:"
    echo "  Add to ~/.bashrc or ~/.zshrc:"
    echo "    source $HEO_PLUGIN_DIR/scripts/shell-alias.sh"
fi
