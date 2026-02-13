#!/bin/bash
# Frosty Plugin Shell Alias
# Source this file in your .bashrc or .zshrc:
#   source /path/to/frosty/scripts/shell-alias.sh

# Detect plugin directory (where this script lives)
FROSTY_PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# Main alias function
claude-frosty() {
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
    cmd+=(--add-dir "$FROSTY_PLUGIN_DIR")

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
alias cf='claude-frosty'

# Worktree-aware variant (auto-loads task context)
claude-frosty-tree() {
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
        claude-frosty --yes --append-system-prompt "$system_prompt" "$@"
    else
        claude-frosty "$@"
    fi
}

# Short alias for tree variant
alias cft='claude-frosty-tree'

# Print help on first source
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Frosty Plugin Aliases"
    echo "====================="
    echo ""
    echo "Usage:"
    echo "  claude-frosty [options]    Launch Claude with frosty plugin"
    echo "  cf                         Short alias for claude-frosty"
    echo "  claude-frosty-tree         Launch in worktree with task context"
    echo "  cft                        Short alias for claude-frosty-tree"
    echo ""
    echo "Options:"
    echo "  -y, --yes                  Skip permission prompts"
    echo "  -p, --prompt <text>        Start with initial prompt"
    echo ""
    echo "Installation:"
    echo "  Add to ~/.bashrc or ~/.zshrc:"
    echo "    source $FROSTY_PLUGIN_DIR/scripts/shell-alias.sh"
fi
