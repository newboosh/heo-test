#!/bin/bash
# Merge Validation Script
#
# Validates that a branch is safe to merge to main
# Checks that no worktree-local files would be merged
#
# Usage: validate-merge-to-main.sh
# Exit codes:
#   0 = Safe to merge
#   1 = Unsafe - worktree files detected

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Check if on main (no merge needed)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "Already on main branch"
    exit 0
fi

echo "Validating merge: $CURRENT_BRANCH → main"
echo ""

# Files that should never be merged to main
declare -a FORBIDDEN_FILES=(
    ".claude-task-context.md"
    ".claude-purpose-context.md"
    ".claude-init.sh"
    ".worktree-scope.json"
    ".pending-terminals.txt"
    ".pending-*"
)

# Get files that would be added/modified in merge
MERGE_FILES=$(git diff main..HEAD --name-only --diff-filter=ACM 2>/dev/null || echo "")

if [ -z "$MERGE_FILES" ]; then
    echo -e "${GREEN}✓ No files to merge${NC}"
    exit 0
fi

# Check each file against forbidden list
VIOLATIONS=0
while IFS= read -r file; do
    for forbidden in "${FORBIDDEN_FILES[@]}"; do
        # Handle glob patterns
        if [[ "$file" == $forbidden ]]; then
            echo -e "${RED}✗ FORBIDDEN: $file${NC}"
            echo "  Reason: Worktree-local file cannot be merged to main"
            VIOLATIONS=$((VIOLATIONS + 1))
            break
        fi
    done
done <<< "$MERGE_FILES"

echo ""

if [ $VIOLATIONS -gt 0 ]; then
    echo -e "${RED}❌ MERGE BLOCKED${NC}"
    echo ""
    echo "Found $VIOLATIONS worktree-local file(s) in merge"
    echo ""
    echo "These files are specific to the worktree and must not reach main."
    echo ""
    echo "To fix:"
    echo "  1. Remove the file from git:"
    echo "     git rm --cached <filename>"
    echo "     git commit -m 'fix: remove worktree-local file'"
    echo ""
    echo "  2. Push the corrected branch:"
    echo "     git push"
    echo ""
    echo "  3. The PR can now be safely merged"
    echo ""
    exit 1
else
    echo -e "${GREEN}✓ Merge validation passed${NC}"
    echo "  No worktree-local files detected"
    echo "  Safe to merge to main"
    exit 0
fi
