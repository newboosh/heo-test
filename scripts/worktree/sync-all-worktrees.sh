#!/bin/bash
# Sync all worktrees with main branch

set -e

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
NC='\033[0m'

# Get main branch
MAIN_BRANCH=$(git -C "$PROJECT_ROOT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

echo -e "${BLUE}🔄 Sync All Worktrees with $MAIN_BRANCH${NC}"
echo "================================"
echo ""

# Get all task worktrees
WORKTREES=($(git -C "$PROJECT_ROOT" worktree list | grep -E "task/|feature/" | awk '{print $1}' | sort))

if [ ${#WORKTREES[@]} -eq 0 ]; then
    echo -e "${RED}No task worktrees found!${NC}"
    exit 1
fi

echo -e "${GREEN}Found ${#WORKTREES[@]} worktrees to sync${NC}"
echo ""

# Confirm
read -p "Pull latest changes from $MAIN_BRANCH in all worktrees? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
CONFLICT_COUNT=0

for i in "${!WORKTREES[@]}"; do
    path="${WORKTREES[$i]}"
    name=$(basename "$path")

    echo -e "${BLUE}[$((i+1))/${#WORKTREES[@]}]${NC} Syncing: ${GREEN}$name${NC}"

    if [ ! -d "$path" ]; then
        echo -e "  ${RED}✗ Path not found${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo ""
        continue
    fi

    cd "$path"

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  ${YELLOW}⚠️  Uncommitted changes - stashing${NC}"
        git stash save "Auto-stash before sync $(date)" >/dev/null 2>&1
        STASHED=1
    else
        STASHED=0
    fi

    # Pull with rebase
    if git pull --rebase origin "$MAIN_BRANCH" 2>&1 | grep -q "CONFLICT"; then
        echo -e "  ${RED}✗ Conflict detected!${NC}"
        echo -e "  ${YELLOW}  Resolve manually in: $path${NC}"
        CONFLICT_COUNT=$((CONFLICT_COUNT + 1))
        # Abort rebase
        git rebase --abort 2>/dev/null || true
    elif git pull --rebase origin "$MAIN_BRANCH" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Synced${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

        # Pop stash if we stashed
        if [ $STASHED -eq 1 ]; then
            if git stash pop >/dev/null 2>&1; then
                echo -e "  ${GREEN}✓ Changes restored${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Stash conflicts - check 'git stash list'${NC}"
            fi
        fi
    else
        echo -e "  ${RED}✗ Failed${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

cd "$PROJECT_ROOT"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Sync complete!${NC}"
echo ""
echo -e "Success: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo -e "Conflicts: ${YELLOW}$CONFLICT_COUNT${NC}"
echo ""

if [ $CONFLICT_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Conflicts detected in some worktrees${NC}"
    echo -e "${YELLOW}   Resolve manually and run again${NC}"
    echo ""
fi

echo -e "${BLUE}Next steps:${NC}"
echo "  /tree status  # Check status of all worktrees"
