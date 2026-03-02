#!/bin/bash
#
# Script: commands/close.sh
# Purpose: DEPRECATED — use /tree reset instead
# Created: 2026-01-28
# Modified: 2026-02-20
# Description: Thin wrapper that prints deprecation warning and delegates to tree_reset.
#              Kept for backwards compatibility only.

# Dependencies: commands/reset.sh must be loaded
# Required variables: TREES_DIR

# /tree close [args...]
# DEPRECATED: Use /tree reset [args...] instead
tree_close() {
    print_warning "'/tree close' is deprecated. Use '/tree reset' instead."
    echo ""
    # Ensure reset module is loaded
    local cmd_file="$COMMANDS_DIR/reset.sh"
    if [ -f "$cmd_file" ] && ! type tree_reset &>/dev/null; then
        source "$cmd_file"
    fi
    tree_reset "$@"
}
