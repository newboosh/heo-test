#!/bin/bash
# Show status of all worktrees

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
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}📊 Worktree Status Dashboard${NC}"
echo "================================"
echo ""

# Get all worktrees
WORKTREES=($(git -C "$PROJECT_ROOT" worktree list | grep -E "task/|feature/" | awk '{print $1}' | sort))

if [ ${#WORKTREES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No worktrees found!${NC}"
    echo ""
    echo "Create worktrees with: /tree stage <description> && /tree build"
    exit 0
fi

echo -e "${GREEN}Total worktrees: ${#WORKTREES[@]}${NC}"
echo ""

# Get current branch for comparison
MAIN_BRANCH=$(git -C "$PROJECT_ROOT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Table header
printf "${CYAN}%-35s %-30s %-15s %-10s${NC}\n" "WORKTREE" "BRANCH" "STATUS" "COMMITS"
printf "${CYAN}%-35s %-30s %-15s %-10s${NC}\n" "--------" "------" "------" "-------"

for path in "${WORKTREES[@]}"; do
    if [ ! -d "$path" ]; then
        continue
    fi

    cd "$path" 2>/dev/null || continue

    # Get info
    name=$(basename "$path")
    branch=$(git branch --show-current 2>/dev/null || echo "DETACHED")

    # Git status
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        status="${YELLOW}MODIFIED${NC}"
    else
        status="${GREEN}CLEAN${NC}"
    fi

    # Commits ahead/behind main
    ahead=$(git rev-list --count origin/$MAIN_BRANCH..HEAD 2>/dev/null || echo "?")
    behind=$(git rev-list --count HEAD..origin/$MAIN_BRANCH 2>/dev/null || echo "?")

    if [ "$ahead" = "0" ] && [ "$behind" = "0" ]; then
        commits="${GREEN}synced${NC}"
    elif [ "$ahead" != "0" ] && [ "$behind" = "0" ]; then
        commits="${CYAN}↑$ahead${NC}"
    elif [ "$ahead" = "0" ] && [ "$behind" != "0" ]; then
        commits="${YELLOW}↓$behind${NC}"
    else
        commits="${YELLOW}↑$ahead↓$behind${NC}"
    fi

    printf "%-35s %-30s %-15b %-10b\n" "$name" "$branch" "$status" "$commits"
done

echo ""
echo -e "${BLUE}Legend:${NC}"
echo -e "  ${GREEN}CLEAN${NC} = No uncommitted changes"
echo -e "  ${YELLOW}MODIFIED${NC} = Uncommitted changes present"
echo -e "  ${CYAN}↑N${NC} = N commits ahead of $MAIN_BRANCH"
echo -e "  ${YELLOW}↓N${NC} = N commits behind $MAIN_BRANCH"
echo -e "  ${GREEN}synced${NC} = Up to date with $MAIN_BRANCH"

echo ""
echo -e "${YELLOW}Quick actions:${NC}"
echo "  /tree status      # This dashboard"
echo "  /tree close       # Mark current worktree complete"
echo "  /tree closedone   # Merge all completed worktrees"
