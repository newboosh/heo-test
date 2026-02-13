#!/bin/bash

# Scope Enforcement Pre-Commit Hook
# Validates that files being committed match the worktree's scope

set -e

# Source scope detection utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scope-detector.sh"

# ==============================================================================
# Configuration
# ==============================================================================

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
SCOPE_JSON=".worktree-scope.json"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# ==============================================================================
# Hook Functions
# ==============================================================================

# Check if we're in a worktree
is_worktree() {
    # Check if .worktree-scope.json exists
    [ -f "$SCOPE_JSON" ]
}

# Get enforcement mode from scope JSON
get_enforcement_mode() {
    if [ ! -f "$SCOPE_JSON" ]; then
        echo "none"
        return
    fi

    python3 <<PYTHON
import json
import sys

try:
    with open("$SCOPE_JSON") as f:
        scope = json.load(f)
    print(scope.get("enforcement", "soft"))
except:
    print("soft")
PYTHON
}

# Validate staged files against scope
validate_staged_files() {
    local enforcement_mode="$1"
    local out_of_scope_files=()
    local in_scope_files=()

    # Get list of staged files (excluding deletions)
    local staged_files=$(git diff --cached --name-only --diff-filter=ACMR)

    if [ -z "$staged_files" ]; then
        return 0
    fi

    # Check each file
    while IFS= read -r file; do
        if file_matches_scope "$file" "$SCOPE_JSON"; then
            in_scope_files+=("$file")
        else
            out_of_scope_files+=("$file")
        fi
    done <<< "$staged_files"

    # Report results
    if [ ${#out_of_scope_files[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Scope Validation Warning${NC}"
        echo ""
        echo "The following files are outside this worktree's defined scope:"
        echo ""
        for file in "${out_of_scope_files[@]}"; do
            echo -e "  ${YELLOW}⚠${NC}  $file"
        done
        echo ""

        # Show worktree info
        if [ -f "$SCOPE_JSON" ]; then
            local worktree_name=$(python3 -c "import json; print(json.load(open('$SCOPE_JSON'))['worktree'])")
            local description=$(python3 -c "import json; print(json.load(open('$SCOPE_JSON'))['description'])")
            echo "Worktree: $worktree_name"
            echo "Description: $description"
            echo ""
        fi

        # Show scope patterns
        echo "Expected scope patterns:"
        python3 <<PYTHON
import json
with open("$SCOPE_JSON") as f:
    scope = json.load(f)
for pattern in scope['scope']['include'][:5]:
    print(f"  • {pattern}")
if len(scope['scope']['include']) > 5:
    print(f"  ... and {len(scope['scope']['include']) - 5} more")
PYTHON
        echo ""

        # Handle based on enforcement mode
        if [ "$enforcement_mode" = "hard" ]; then
            echo -e "${RED}❌ Hard enforcement enabled - commit blocked${NC}"
            echo ""
            echo "Options:"
            echo "  1. Only commit in-scope files"
            echo "  2. Update .worktree-scope.json to include these files"
            echo "  3. Change enforcement mode to 'soft' in .worktree-scope.json"
            echo ""
            return 1
        else
            echo -e "${GREEN}✓ Soft enforcement - proceeding with warning${NC}"
            echo ""
            echo "These files will be committed, but consider:"
            echo "  1. Are these changes related to this worktree's purpose?"
            echo "  2. Should .worktree-scope.json be updated?"
            echo "  3. Would these changes be better in a different worktree?"
            echo ""
        fi
    else
        if [ ${#in_scope_files[@]} -gt 0 ]; then
            echo -e "${GREEN}✓ All staged files are within scope${NC} (${#in_scope_files[@]} files)"
        fi
    fi

    return 0
}

# ==============================================================================
# Main Hook Logic
# ==============================================================================

main() {
    # Only run in worktrees with scope configuration
    if ! is_worktree; then
        # No scope file = main workspace or old worktree, skip validation
        exit 0
    fi

    # Get enforcement mode
    local enforcement_mode=$(get_enforcement_mode)

    # Skip if enforcement is disabled
    if [ "$enforcement_mode" = "none" ]; then
        exit 0
    fi

    # Validate staged files
    if ! validate_staged_files "$enforcement_mode"; then
        exit 1
    fi

    exit 0
}

# Run hook
main "$@"
