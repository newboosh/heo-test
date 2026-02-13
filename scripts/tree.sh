#!/bin/bash
#
# Script: tree.sh
# Purpose: Worktree management system for parallel development
# Created: 2024-10-09
# Modified: 2026-01-28
# Usage: /tree <command> [options]
# Commands: stage, list, build, close, closedone, status, conflict, help
# Related: .claude/commands/tree.md, docs/worktrees/WORKTREE_COMPLETE_GUIDE.md
# Description: Entry point for modular worktree lifecycle management

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/tree/main.sh" "$@"
