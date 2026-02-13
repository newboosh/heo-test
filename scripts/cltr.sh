#!/bin/bash
# Claude Tree Context Loader

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get frosty plugin directory (parent of this script's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FROSTY_PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find the current worktree root
WORKTREE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$WORKTREE_ROOT" ]; then
    echo -e "${RED}Error: Not in a git repository or worktree${NC}"
    exit 1
fi

# Context file location
CONTEXT_FILE="${WORKTREE_ROOT}/.claude-task-context.md"

# Check if context file exists
if [ ! -f "$CONTEXT_FILE" ]; then
    echo -e "${YELLOW}Warning: No task context file found at ${CONTEXT_FILE}${NC}"
    read -p "Would you like to create a task context file? (y/n): " create_context
    
    if [[ "$create_context" =~ ^[Yy]$ ]]; then
        cat > "$CONTEXT_FILE" << TEMPLATE
# Task Context for $(basename "$WORKTREE_ROOT") Worktree

## Description
[Provide a clear, concise description of the task or feature]

## Objectives
- [ ] Key Objective 1
- [ ] Key Objective 2
- [ ] Key Objective 3

## Technical Requirements
- 

## Constraints
- 

## Additional Notes
TEMPLATE
        echo -e "${GREEN}Task context template created. Please edit ${CONTEXT_FILE}${NC}"
        nano "$CONTEXT_FILE"
    else
        echo -e "${BLUE}Proceeding without context file...${NC}"
    fi
fi

# Detect worktree name
WORKTREE_NAME=$(basename "$WORKTREE_ROOT")

# Set terminal title to "claude <worktree-name>"
echo -ne "\033]0;claude $WORKTREE_NAME\007"

# Launch Claude
echo -e "${GREEN}🌳 Claude Tree Context Loader ${NC}"
echo -e "${BLUE}Worktree:${NC} $WORKTREE_NAME"
echo -e "${BLUE}Context:${NC} $CONTEXT_FILE"
echo ""

# Build plugin args if plugin exists
PLUGIN_ARGS=""
if [ -f "$FROSTY_PLUGIN_DIR/.claude-plugin/plugin.json" ]; then
    PLUGIN_ARGS="--add-dir $FROSTY_PLUGIN_DIR"
    echo -e "${BLUE}Plugin:${NC} $FROSTY_PLUGIN_DIR"
fi

claude $PLUGIN_ARGS --dangerously-skip-permissions \
       --append-system-prompt "You are working in a git worktree dedicated to this task:

Context loaded from: $CONTEXT_FILE

IMPORTANT: Immediately read the .claude-task-context.md file to understand the full task details, then ask 1-3 clarifying questions to ensure you understand the scope and requirements before beginning implementation. Focus on:
1. Ambiguous requirements that need clarification
2. Technical decisions that aren't specified
3. Edge cases or error handling expectations
4. Integration points with existing code

Wait for user responses before starting implementation."
