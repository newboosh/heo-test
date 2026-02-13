#!/bin/bash
# Worktree Commit Guard Hook
#
# Pre-commit hook that prevents worktree-local files from being committed
# Runs as FIRST hook in master pre-commit chain (highest priority)
#
# These files are generated per-worktree and must NEVER reach main:
# - .claude-task-context.md (Claude task context)
# - .claude-purpose-context.md (Purpose context)
# - .claude-init.sh (Worktree launch script)
# - .worktree-scope.json (Worktree scope manifest)
# - PURPOSE.md (Worktree-specific purpose document)
# - .pending-terminals.txt (Temporary pending state)
# - .pending-* (Any temporary pending files)
#
# Exit codes:
#   0 = No worktree-local files in staging area
#   1 = Worktree-local files detected - commit blocked

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Files that are worktree-local and should never be committed
declare -a WORKTREE_LOCAL_FILES=(
    ".claude-task-context.md"
    ".claude-purpose-context.md"
    ".claude-init.sh"
    ".worktree-scope.json"
    "PURPOSE.md"
    ".pending-terminals.txt"
)

# Get list of staged files
staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")

if [ -z "$staged_files" ]; then
    # No files staged, nothing to check
    exit 0
fi

# Check exact matches for main files
violations=0
pending_violations=()

for file in "${WORKTREE_LOCAL_FILES[@]}"; do
    if echo "$staged_files" | grep -q "^$file\$"; then
        echo -e "${RED}✗ ERROR${NC}: Worktree-local file cannot be committed: $file"
        violations=$((violations + 1))
    fi
done

# Also check for .pending-* patterns (glob match)
while IFS= read -r file; do
    if [[ "$file" == .pending-* ]]; then
        echo -e "${RED}✗ ERROR${NC}: Worktree-local file cannot be committed: $file"
        pending_violations+=("$file")
        violations=$((violations + 1))
    fi
done <<< "$staged_files"

if [ $violations -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Commit blocked: $violations worktree-local file(s) in staging area${NC}"
    echo ""
    echo "These files are specific to this worktree and must not be merged to main:"
    echo ""
    for file in "${WORKTREE_LOCAL_FILES[@]}"; do
        if echo "$staged_files" | grep -q "^$file\$"; then
            echo -e "  ${BLUE}•${NC} $file"
        fi
    done

    if [ ${#pending_violations[@]} -gt 0 ]; then
        for file in "${pending_violations[@]}"; do
            echo -e "  ${BLUE}•${NC} $file"
        done
    fi

    echo ""
    echo "To fix, remove these files from staging:"
    echo ""

    for file in "${WORKTREE_LOCAL_FILES[@]}"; do
        if echo "$staged_files" | grep -q "^$file\$"; then
            echo "  git reset HEAD \"$file\""
        fi
    done

    if [ ${#pending_violations[@]} -gt 0 ]; then
        for file in "${pending_violations[@]}"; do
            echo "  git reset HEAD \"$file\""
        done
    fi

    echo ""
    echo "Then verify they're in .gitignore and commit again."
    echo ""
    exit 1
fi

exit 0
