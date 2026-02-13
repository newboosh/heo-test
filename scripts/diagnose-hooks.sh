#!/bin/bash
#
# Diagnose frosty hooks issues
#
# Run this script to check for problems with hook execution
# and to enable/disable hooks quickly if issues occur.
#
# Usage:
#   ./scripts/diagnose-hooks.sh         # Run diagnostics
#   ./scripts/diagnose-hooks.sh disable # Disable all hooks
#   ./scripts/diagnose-hooks.sh enable  # Re-enable hooks
#   ./scripts/diagnose-hooks.sh logs    # Show recent log entries
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PLUGIN_ROOT}/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Frosty Hooks Diagnostic Tool"
echo "========================================"
echo ""

# Handle commands
case "${1:-diagnose}" in
    disable)
        echo -e "${YELLOW}To disable hooks:${NC}"
        echo ""
        echo "Note: This script runs in a subshell, so export/unset won't persist."
        echo ""
        echo "Option 1 - Run in your current shell:"
        echo "  export FROSTY_DISABLE_HOOKS=1"
        echo ""
        echo "Option 2 - Add to your shell profile (~/.bashrc or ~/.zshrc):"
        echo "  export FROSTY_DISABLE_HOOKS=1"
        echo ""
        echo "Option 3 - Create a skip file in the project (persists):"
        echo "  touch .frosty-skip-hooks"
        echo ""
        exit 0
        ;;
    enable)
        echo -e "${GREEN}To re-enable hooks:${NC}"
        echo ""
        echo "Note: This script runs in a subshell, so export/unset won't persist."
        echo ""
        echo "Option 1 - Run in your current shell:"
        echo "  unset FROSTY_DISABLE_HOOKS"
        echo ""
        echo "Option 2 - Remove from your shell profile if added."
        echo ""
        echo "Option 3 - Remove the skip file if created:"
        echo "  rm -f .frosty-skip-hooks"
        echo ""
        exit 0
        ;;
    logs)
        echo "Recent log entries:"
        echo "------------------"
        # Honour FROSTY_LOG_FILE env var if set
        if [ -n "$FROSTY_LOG_FILE" ] && [ -f "$FROSTY_LOG_FILE" ]; then
            tail -50 "$FROSTY_LOG_FILE"
        elif [ -d "$LOG_DIR" ]; then
            # Find most recent log file
            LOG_FILE=$(ls -t "$LOG_DIR"/hooks-*.log 2>/dev/null | head -1)
            if [ -n "$LOG_FILE" ]; then
                tail -50 "$LOG_FILE"
            else
                echo "No log files found in $LOG_DIR"
            fi
        else
            echo "Log directory not found: $LOG_DIR"
            echo "Enable logging with: export FROSTY_LOG_FILE=~/.frosty/hooks.log"
        fi
        exit 0
        ;;
esac

# Run diagnostics
echo "Checking environment..."
echo ""

# Check Python
echo -n "Python: "
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}$PYTHON_VERSION${NC}"
else
    echo -e "${RED}NOT FOUND${NC}"
fi

# Check Git
echo -n "Git: "
if command -v git &>/dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    echo -e "${GREEN}$GIT_VERSION${NC}"
else
    echo -e "${RED}NOT FOUND${NC}"
fi

# Check tools
echo ""
echo "Checking tools (used by hooks)..."
for tool in black flake8 vulture ruff; do
    echo -n "  $tool: "
    if command -v "$tool" &>/dev/null; then
        echo -e "${GREEN}available${NC}"
    else
        echo -e "${YELLOW}not found (hooks will skip)${NC}"
    fi
done

# Check environment variables
echo ""
echo "Environment variables:"
echo -n "  FROSTY_DISABLE_HOOKS: "
if [ -n "$FROSTY_DISABLE_HOOKS" ]; then
    echo -e "${YELLOW}SET (hooks disabled)${NC}"
else
    echo -e "${GREEN}not set${NC}"
fi

echo -n "  FROSTY_FORCE_ENABLE: "
if [ -n "$FROSTY_FORCE_ENABLE" ]; then
    echo -e "${YELLOW}SET (forcing hooks in all projects)${NC}"
else
    echo -e "${GREEN}not set${NC}"
fi

echo -n "  FROSTY_DEBUG: "
if [ -n "$FROSTY_DEBUG" ]; then
    echo -e "${YELLOW}SET (verbose output)${NC}"
else
    echo "not set"
fi

echo -n "  FROSTY_LOG_FILE: "
if [ -n "$FROSTY_LOG_FILE" ]; then
    echo -e "${GREEN}$FROSTY_LOG_FILE${NC}"
else
    echo "not set (logging disabled)"
fi

# Check project markers
echo ""
echo "Project detection (current directory):"
CWD=$(pwd)
echo "  Working directory: $CWD"

MARKERS=(".claude/hooks.json" ".claude/settings.local.json" "CLAUDE.md")
FOUND_MARKER=false
for marker in "${MARKERS[@]}"; do
    if [ -f "$CWD/$marker" ]; then
        echo -e "  ${GREEN}Found: $marker${NC}"
        FOUND_MARKER=true
    fi
done

if [ -f "$CWD/.frosty-skip-hooks" ]; then
    echo -e "  ${YELLOW}Found: .frosty-skip-hooks (hooks will be skipped)${NC}"
fi

if [ "$FOUND_MARKER" = false ]; then
    echo -e "  ${YELLOW}No frosty marker files found${NC}"
    echo "  Hooks will be skipped in this directory unless FROSTY_FORCE_ENABLE=1"
fi

# Check hooks directory
echo ""
echo "Hooks status:"
HOOKS_DIR="$PLUGIN_ROOT/hooks"
if [ -d "$HOOKS_DIR" ]; then
    HOOK_COUNT=$(find "$HOOKS_DIR" -maxdepth 1 -name "*.py" | wc -l | tr -d ' ')
    echo -e "  ${GREEN}Found $HOOK_COUNT hook scripts in $HOOKS_DIR${NC}"
else
    echo -e "  ${RED}Hooks directory not found: $HOOKS_DIR${NC}"
fi

# Check safeguards module
echo ""
echo "Safeguards module:"
SAFEGUARDS="$HOOKS_DIR/lib/safeguards.py"
if [ -f "$SAFEGUARDS" ]; then
    echo -e "  ${GREEN}Safeguards installed${NC}"
    echo "  Primary protection: project scope validation"
    echo "  Emergency limits: 20 subprocesses/hook, 100 files/operation"
else
    echo -e "  ${RED}Safeguards NOT installed${NC}"
fi

# Check log files
echo ""
echo "Log files:"
if [ -d "$LOG_DIR" ]; then
    LOG_COUNT=$(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l | tr -d ' ')
    if [ "$LOG_COUNT" -gt 0 ]; then
        echo "  Found $LOG_COUNT log file(s) in $LOG_DIR"
        LATEST_LOG=$(ls -t "$LOG_DIR"/hooks-*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            LOG_SIZE=$(du -h "$LATEST_LOG" | cut -f1)
            LOG_LINES=$(wc -l < "$LATEST_LOG" | tr -d ' ')
            echo "  Latest: $(basename "$LATEST_LOG") ($LOG_SIZE, $LOG_LINES entries)"
        fi
    else
        echo "  No log files found"
    fi
else
    echo "  Log directory not created yet"
fi

echo ""
echo "========================================"
echo ""
echo "If you're experiencing issues:"
echo ""
echo "1. Disable hooks temporarily:"
echo "   export FROSTY_DISABLE_HOOKS=1"
echo ""
echo "2. Enable debug logging:"
echo "   export FROSTY_DEBUG=1"
echo "   export FROSTY_LOG_FILE=~/.frosty/hooks.log"
echo ""
echo "3. Check logs:"
echo "   ./scripts/diagnose-hooks.sh logs"
echo ""
echo "4. Skip hooks in a specific project:"
echo "   touch .frosty-skip-hooks"
echo ""
