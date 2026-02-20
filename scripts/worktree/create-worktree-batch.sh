#!/bin/bash
# Worktree Batch Creator - Create multiple worktrees from a task list

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$PROJECT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌳 Worktree Batch Creator${NC}"
echo "================================"
echo ""

# Check if tasks file provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <tasks-file> [base-branch]${NC}"
    echo ""
    echo "Example tasks file format:"
    echo "---"
    echo "claude-refinement:Claude.md refinement and agent creation"
    echo "marketing-content:Marketing automation content generation"
    echo "script-testing:Script testing framework"
    echo "---"
    echo ""
    echo "Each line: <worktree-name>:<description>"
    exit 1
fi

TASKS_FILE="$1"
BASE_BRANCH="${2:-main}"

if [ ! -f "$TASKS_FILE" ]; then
    echo -e "${RED}Error: Tasks file not found: $TASKS_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}Base branch:${NC} $BASE_BRANCH"
echo -e "${GREEN}Tasks file:${NC} $TASKS_FILE"
echo ""

# Count tasks
TASK_COUNT=$(grep -v '^#' "$TASKS_FILE" | grep -v '^$' | wc -l | xargs)
echo -e "${BLUE}Found $TASK_COUNT tasks${NC}"
echo ""

# Confirm
read -p "Create $TASK_COUNT worktrees? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${GREEN}Creating worktrees...${NC}"
echo ""

TASK_NUM=0
SUCCESS_COUNT=0
FAIL_COUNT=0

# Read tasks and create worktrees
while IFS=':' read -r worktree_name description || [ -n "$worktree_name" ]; do
    # Skip comments and empty lines
    [[ "$worktree_name" =~ ^#.*$ ]] && continue
    [[ -z "$worktree_name" ]] && continue

    TASK_NUM=$((TASK_NUM + 1))
    BRANCH_NAME="task/$(printf "%02d" $TASK_NUM)-$worktree_name"
    WORKTREE_PATH="$PROJECT_ROOT/.trees/$worktree_name"

    echo -e "${BLUE}[$TASK_NUM/$TASK_COUNT]${NC} Creating: ${GREEN}$worktree_name${NC}"
    echo "  Branch: $BRANCH_NAME"
    echo "  Path: $WORKTREE_PATH"

    # Check if worktree already exists
    if [ -d "$WORKTREE_PATH" ]; then
        echo -e "  ${YELLOW}⚠️  Already exists, skipping${NC}"
        echo ""
        continue
    fi

    # Create worktree
    if git -C "$PROJECT_ROOT" worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" "$BASE_BRANCH" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Success${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

        # Create task README
        cat > "$WORKTREE_PATH/PURPOSE.md" << EOF
# Task: $description

**Worktree:** $worktree_name
**Branch:** $BRANCH_NAME
**Base:** $BASE_BRANCH
**Created:** $(date +"%Y-%m-%d %H:%M:%S")

## Scope
$description

## Primary Files
- (Add files as you work)

## Conflict Warnings
- (Note potential conflicts with other tasks)

## Status
- [ ] Planning
- [ ] Development
- [ ] Testing
- [ ] Ready for merge

## Notes
(Add notes here)
EOF
        echo -e "  ${GREEN}✓ Created PURPOSE.md${NC}"

        # Create Claude task context file
        cat > "$WORKTREE_PATH/.claude-purpose-context.md" << EOF
# Task $TASK_NUM: $description

**Worktree:** $worktree_name
**Branch:** $BRANCH_NAME
**Status:** In Progress
**Created:** $(date +"%Y-%m-%d")

## Objective
$description

## Scope
Complete the following deliverables for this task. See PURPOSE.md for more details.

## Primary Files
- PURPOSE.md (task documentation)
- (Files will be listed here as work progresses)

## Success Criteria
- [ ] Planning phase complete
- [ ] Implementation complete
- [ ] Testing complete
- [ ] Documentation updated
- [ ] Ready for merge

## Important Notes
- This is worktree $TASK_NUM of a parallel development workflow
- Branch: $BRANCH_NAME based on $BASE_BRANCH
- Check PURPOSE.md for conflict warnings with other tasks
- Use /tree status to see all worktree statuses

## Workflow Commands
- Check status: /tree status
- Remove worktree when done: /tree close

Focus on this specific task and its objectives.
EOF
        echo -e "  ${GREEN}✓ Created .claude-purpose-context.md${NC}"

        # Create .claude directory if it doesn't exist
        mkdir -p "$WORKTREE_PATH/.claude"

        # Create Claude startup script
        cat > "$WORKTREE_PATH/.claude/init.sh" << 'EOFSCRIPT'
#!/bin/bash
# Claude Code Auto-Startup Script
# Automatically loads task context and launches Claude

WORKTREE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_CONTEXT="$WORKTREE_ROOT/.claude-purpose-context.md"

# Display task information
if [ -f "$TASK_CONTEXT" ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           Claude Code - Purpose Context Loaded                   ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    head -15 "$TASK_CONTEXT"
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    echo "Starting Claude Code with task context..."
    echo "────────────────────────────────────────────────────────────────"
    echo ""
fi

# Change to worktree root
cd "$WORKTREE_ROOT"

# Launch Claude with task context
if [ -f "$TASK_CONTEXT" ]; then
    CONTEXT=$(cat "$TASK_CONTEXT")
    exec claude --append-system-prompt "

# PURPOSE CONTEXT - YOU ARE WORKING IN A WORKTREE

$CONTEXT

IMPORTANT:
- You are in a dedicated worktree for this specific task
- Focus exclusively on this task's objectives
- Refer to .claude-purpose-context.md and PURPOSE.md for details
- This is part of a parallel development workflow with multiple worktrees
- Do not work on files outside this task's scope
"
else
    echo "Warning: Task context file not found at $TASK_CONTEXT"
    echo "Launching Claude without task context..."
    exec claude
fi
EOFSCRIPT

        chmod +x "$WORKTREE_PATH/.claude/init.sh"
        echo -e "  ${GREEN}✓ Created .claude/init.sh${NC}"

    else
        echo -e "  ${RED}✗ Failed${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done < "$TASKS_FILE"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Worktree creation complete!${NC}"
echo ""
echo -e "Created: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo -e "Total: $TASK_COUNT"
echo ""

# Show worktree list
echo -e "${BLUE}Current worktrees:${NC}"
git -C "$PROJECT_ROOT" worktree list | grep -E "task/|feature/" | head -20

echo ""
echo -e "${BLUE}Generating VS Code terminal profiles...${NC}"

# Generate VS Code settings for terminal profiles
VSCODE_DIR="$PROJECT_ROOT/.vscode"
mkdir -p "$VSCODE_DIR"

# Create terminal profiles in settings.json
SETTINGS_FILE="$VSCODE_DIR/settings.json"

# Read existing settings or create empty object
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}  Backing up existing settings.json${NC}"
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"
fi

# Generate terminal profile configuration
cat > "$VSCODE_DIR/terminal-profiles.json" << 'EOFPROFILES'
{
  "terminal.integrated.profiles.linux": {
EOFPROFILES

# Add profile for each worktree
TASK_NUM=0
TERMINAL_COLORS=("Blue" "Green" "Yellow" "Cyan" "Magenta" "Red")

while IFS=':' read -r worktree_name description || [ -n "$worktree_name" ]; do
    # Skip comments and empty lines
    [[ "$worktree_name" =~ ^#.*$ ]] && continue
    [[ -z "$worktree_name" ]] && continue

    TASK_NUM=$((TASK_NUM + 1))
    WORKTREE_PATH="$PROJECT_ROOT/.trees/$worktree_name"

    # Skip if worktree doesn't exist
    [ ! -d "$WORKTREE_PATH" ] && continue

    # Get terminal color (cycle through colors)
    COLOR_INDEX=$(( (TASK_NUM - 1) % ${#TERMINAL_COLORS[@]} ))
    COLOR="${TERMINAL_COLORS[$COLOR_INDEX]}"

    # Add comma if not first entry
    [ $TASK_NUM -gt 1 ] && echo "," >> "$VSCODE_DIR/terminal-profiles.json"

    # Create profile entry (use variable for path)
    cat >> "$VSCODE_DIR/terminal-profiles.json" << EOF
    "Task $TASK_NUM: $worktree_name": {
      "path": "/bin/bash",
      "args": ["-c", "cd $WORKTREE_PATH && exec bash"],
      "color": "terminal.ansi$COLOR",
      "icon": "tree"
    }
EOF
done < "$TASKS_FILE"

# Close the profiles object
cat >> "$VSCODE_DIR/terminal-profiles.json" << 'EOFPROFILES'
  }
}
EOFPROFILES

echo -e "${GREEN}  ✓ Created terminal-profiles.json${NC}"

# Create .trees directory if needed
mkdir -p "$PROJECT_ROOT/.trees"

# Create helper script to launch all Claude sessions
cat > "$PROJECT_ROOT/.trees/launch-all-claude.sh" << EOFLAUNCH
#!/bin/bash
# Launch Claude Code in all worktrees

PROJECT_ROOT="\$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TREES_DIR="\$PROJECT_ROOT/.trees"

echo "🚀 Launching Claude Code in all worktrees..."
echo ""

# Get all task worktrees
WORKTREES=(\$(find "\$TREES_DIR" -maxdepth 1 -type d -name "*" -not -name ".*" | sort))

for path in "\${WORKTREES[@]}"; do
    if [ -f "\$path/.claude/init.sh" ]; then
        name=\$(basename "\$path")
        echo "Starting Claude in: \$name"

        # Launch in new tmux window if tmux is available
        if command -v tmux &> /dev/null; then
            tmux new-window -n "\$name" -c "\$path" "\$path/.claude/init.sh" 2>/dev/null || true
        else
            echo "  Run manually: cd \$path && ./.claude/init.sh"
        fi
    fi
done

echo ""
echo "✓ All Claude sessions started"
echo ""
echo "To switch between tmux windows:"
echo "  Ctrl+b then window number (0-9)"
echo "  Ctrl+b then 'w' to list all windows"
EOFLAUNCH

chmod +x "$PROJECT_ROOT/.trees/launch-all-claude.sh"
echo -e "${GREEN}  ✓ Created launch-all-claude.sh${NC}"

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Open VS Code terminal profiles (Terminal → New Terminal → Select profile)"
echo "2. Or use: ./.trees/launch-all-claude.sh (launches Claude in all worktrees with tmux)"
echo "3. In each worktree terminal, run: ./.claude/init.sh"
echo ""
echo -e "${CYAN}To start Claude with task context:${NC}"
echo "  cd $PROJECT_ROOT/.trees/<worktree-name>"
echo "  ./.claude/init.sh"
echo ""
echo -e "${CYAN}Terminal profiles created in:${NC}"
echo "  $VSCODE_DIR/terminal-profiles.json"
