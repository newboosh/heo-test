#!/bin/bash
# Open terminals for all worktrees automatically

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$PROJECT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

TREES_DIR="$PROJECT_ROOT/.trees"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Worktree Terminal Launcher${NC}"
echo "================================"
echo ""

# Get all task worktrees
WORKTREES=($(git -C "$PROJECT_ROOT" worktree list | grep -E "\[task/|\[feature/" | awk '{print $1}' | sort))

if [ ${#WORKTREES[@]} -eq 0 ]; then
    echo -e "${RED}No task worktrees found!${NC}"
    exit 1
fi

echo -e "${GREEN}Found ${#WORKTREES[@]} task worktrees${NC}"
echo ""

# Check for terminal multiplexer
if command -v tmux &> /dev/null; then
    MULTIPLEXER="tmux"
elif command -v screen &> /dev/null; then
    MULTIPLEXER="screen"
else
    MULTIPLEXER="none"
fi

echo -e "${BLUE}Terminal multiplexer:${NC} $MULTIPLEXER"
echo ""

# Function to open with tmux
open_tmux() {
    SESSION_NAME="worktrees-$(date +%s)"

    echo -e "${GREEN}Creating tmux session: $SESSION_NAME${NC}"
    echo ""

    # Create session with first worktree
    tmux new-session -d -s "$SESSION_NAME" -n "Main" -c "$PROJECT_ROOT"

    # Add window for each worktree
    for i in "${!WORKTREES[@]}"; do
        path="${WORKTREES[$i]}"
        name=$(basename "$path")
        task_num=$(echo "$name" | grep -oP '(?<=task/).*' || echo "$name")

        echo -e "  ${GREEN}[$((i+1))/${#WORKTREES[@]}]${NC} $name"
        tmux new-window -t "$SESSION_NAME" -n "$task_num" -c "$path"
    done

    # Select first window
    tmux select-window -t "$SESSION_NAME:1"

    echo ""
    echo -e "${GREEN}✓ Tmux session created: $SESSION_NAME${NC}"
    echo ""
    echo -e "${YELLOW}To attach:${NC} tmux attach -t $SESSION_NAME"
    echo -e "${YELLOW}To list windows:${NC} Ctrl+b then w"
    echo -e "${YELLOW}To switch:${NC} Ctrl+b then 0-9"
    echo -e "${YELLOW}To detach:${NC} Ctrl+b then d"
    echo ""

    # Auto-attach if in interactive shell
    if [ -t 0 ]; then
        read -p "Attach now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            tmux attach -t "$SESSION_NAME"
        fi
    fi
}

# Function to open with screen
open_screen() {
    SESSION_NAME="worktrees-$(date +%s)"

    echo -e "${GREEN}Creating screen session: $SESSION_NAME${NC}"
    echo ""

    # Create session
    screen -dmS "$SESSION_NAME"

    # Add window for each worktree
    for i in "${!WORKTREES[@]}"; do
        path="${WORKTREES[$i]}"
        name=$(basename "$path")
        task_num=$(echo "$name" | grep -oP '(?<=task/).*' || echo "$name")

        echo -e "  ${GREEN}[$((i+1))/${#WORKTREES[@]}]${NC} $name"
        screen -S "$SESSION_NAME" -X screen -t "$task_num" bash -c "cd $path; exec bash"
    done

    echo ""
    echo -e "${GREEN}✓ Screen session created: $SESSION_NAME${NC}"
    echo ""
    echo -e "${YELLOW}To attach:${NC} screen -r $SESSION_NAME"
    echo -e "${YELLOW}To switch:${NC} Ctrl+a then window number"
    echo -e "${YELLOW}To detach:${NC} Ctrl+a then d"
    echo ""

    # Auto-attach if in interactive shell
    if [ -t 0 ]; then
        read -p "Attach now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            screen -r "$SESSION_NAME"
        fi
    fi
}

# Function to show manual commands
show_manual() {
    echo -e "${YELLOW}Terminal multiplexer not available${NC}"
    echo ""
    echo -e "${BLUE}Open terminals manually:${NC}"
    echo ""

    for i in "${!WORKTREES[@]}"; do
        path="${WORKTREES[$i]}"
        name=$(basename "$path")
        echo -e "${GREEN}# Task $((i+1)):${NC} $name"
        echo "cd $path"
        echo ""
    done

    echo -e "${YELLOW}Or install tmux/screen:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install tmux"
    echo "  macOS: brew install tmux"
}

# Generate VS Code workspace file
generate_vscode_workspace() {
    WORKSPACE_FILE="$PROJECT_ROOT/worktrees.code-workspace"

    echo -e "${BLUE}Generating VS Code workspace file...${NC}"

    cat > "$WORKSPACE_FILE" << 'EOHEADER'
{
  "folders": [
    {
      "name": "📦 Main Workspace",
      "path": "."
    },
EOHEADER

    for i in "${!WORKTREES[@]}"; do
        path="${WORKTREES[$i]}"
        name=$(basename "$path")
        task_num=$(echo "$name" | sed 's/task\///')

        # Add comma if not first item
        [ $i -gt 0 ] && echo "," >> "$WORKSPACE_FILE"

        cat >> "$WORKSPACE_FILE" << EOF
    {
      "name": "🌳 $task_num",
      "path": "$path"
    }
EOF
    done

    cat >> "$WORKSPACE_FILE" << 'EOFOOTER'
  ],
  "settings": {
    "files.watcherExclude": {
      "**/.git/objects/**": true,
      "**/.git/subtree-cache/**": true,
      "**/node_modules/**": true
    }
  }
}
EOFOOTER

    echo -e "${GREEN}✓ Created: $WORKSPACE_FILE${NC}"
    echo ""
    echo -e "${YELLOW}To use:${NC}"
    echo "  1. File → Open Workspace from File..."
    echo "  2. Select: worktrees.code-workspace"
    echo "  3. Each worktree appears as a folder in sidebar"
}

# Main execution
case "$MULTIPLEXER" in
    tmux)
        open_tmux
        ;;
    screen)
        open_screen
        ;;
    *)
        show_manual
        ;;
esac

# Always generate VS Code workspace
echo ""
generate_vscode_workspace

echo ""
echo -e "${GREEN}✓ Terminal launcher complete${NC}"
