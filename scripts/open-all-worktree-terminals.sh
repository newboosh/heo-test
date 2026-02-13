#!/bin/bash
# Helper script to manually open terminals for all worktrees
# Usage: Run this script, then manually execute the commands it outputs

TREES_DIR="/workspace/.trees"

echo "==================================================================="
echo "Manual Terminal Setup for Worktrees"
echo "==================================================================="
echo ""
echo "Since automated terminal creation doesn't work in devcontainers,"
echo "you'll need to manually create terminals. Here's how:"
echo ""
echo "METHOD 1: VS Code Terminal Panel (Recommended)"
echo "----------------------------------------------"
echo "1. Open the Terminal panel (View → Terminal or Ctrl+\`)"
echo "2. For each worktree below, click the '+' dropdown → 'bash'"
echo "3. In the new terminal, paste the command shown"
echo ""
echo "METHOD 2: Copy/Paste All Commands"
echo "----------------------------------"
echo "Copy each command below and run in separate terminals:"
echo ""

terminal_num=1
for worktree_path in "$TREES_DIR"/*/ ; do
    # Skip hidden directories
    worktree_name=$(basename "$worktree_path")
    [[ "$worktree_name" == .* ]] && continue

    echo "# Terminal $terminal_num: $worktree_name"
    echo "cd $worktree_path && bash .claude-init.sh"
    echo ""

    terminal_num=$((terminal_num + 1))
done

echo "==================================================================="
echo "Total: $((terminal_num - 1)) worktrees"
echo "==================================================================="
echo ""
echo "TIP: After running .claude-init.sh in each terminal, Claude will"
echo "     auto-launch with the task context for that worktree."
echo ""
