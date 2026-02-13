#!/bin/bash
#
# Script: main.sh (new modular tree.sh)
# Purpose: Worktree management system for parallel development
# Created: 2026-01-28
# Modified: 2026-01-28
# Usage: /tree <command> [options]
# Commands: stage, list, build, close, closedone, status, conflict, help
# Description: Complete worktree lifecycle management - modular version

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
COMMANDS_DIR="$SCRIPT_DIR/commands"

# Dynamic workspace detection
# Use --git-common-dir to find the MAIN repo root, even from inside a worktree.
# git rev-parse --show-toplevel returns the worktree root (wrong for .trees/ paths),
# while --git-common-dir always returns the main repo's .git/ directory.
_GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
if [ -n "$_GIT_COMMON_DIR" ]; then
    # Normalize to absolute path (git-common-dir can return relative ".git")
    if [[ "$_GIT_COMMON_DIR" != /* ]]; then
        _GIT_COMMON_DIR="$(cd "$_GIT_COMMON_DIR" && pwd)"
    fi
    # Main repo root is the parent of .git/
    WORKSPACE_ROOT="$(cd "$_GIT_COMMON_DIR/.." && pwd)"
else
    WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
unset _GIT_COMMON_DIR

# Standard paths
TREES_DIR="$WORKSPACE_ROOT/.trees"
COMPLETED_DIR="$TREES_DIR/.completed"
INCOMPLETE_DIR="$TREES_DIR/.incomplete"
ARCHIVED_DIR="$TREES_DIR/.archived"
CONFLICT_BACKUP_DIR="$TREES_DIR/.conflict-backup"
STAGED_FEATURES_FILE="$TREES_DIR/.staged-features.txt"
BUILD_STATE_FILE="$TREES_DIR/.build_state.json"
GIT_OPERATION_LOCK="$WORKSPACE_ROOT/.git/.git-operation.lock"
GIT_OPERATION_LOG="$WORKSPACE_ROOT/.git/.git-operations.log"
TREE_CONFIG_FILE="$WORKSPACE_ROOT/worktree-config.json"

# Export for submodules
export WORKSPACE_ROOT TREES_DIR COMPLETED_DIR INCOMPLETE_DIR ARCHIVED_DIR
export CONFLICT_BACKUP_DIR STAGED_FEATURES_FILE BUILD_STATE_FILE
export GIT_OPERATION_LOCK GIT_OPERATION_LOG SCRIPT_DIR TREE_CONFIG_FILE

#==============================================================================
# Load Library Modules
#==============================================================================

# Load core libraries
source "$LIB_DIR/config.sh"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/git-safety.sh"
source "$LIB_DIR/validation.sh"
source "$LIB_DIR/state.sh"
source "$LIB_DIR/setup.sh"

# Load config (may fail gracefully if jq not installed)
load_config || true

# Source scope detection utilities (requires bash 4+ for associative arrays)
PARENT_SCRIPT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ "${BASH_VERSINFO[0]}" -ge 4 ]] && [ -f "$PARENT_SCRIPT_DIR/scope-detector.sh" ]; then
    source "$PARENT_SCRIPT_DIR/scope-detector.sh"
else
    # Stub functions for macOS bash 3.x compatibility
    detect_scope() { echo "[]"; }
    detect_scope_from_description() { echo '{"scope":{"include":["**/*"],"exclude":[]},"enforcement":"soft"}'; }
    calculate_librarian_scope() { echo '{"scope":{"include":["docs/**","*.md","scripts/**"],"exclude":[]},"enforcement":"soft"}'; }
    detect_scope_conflicts() { return 0; }
    if [[ "${BASH_VERSINFO[0]}" -lt 4 ]]; then
        debug "Note: Scope detection requires bash 4+. Running in compatibility mode."
    fi
fi

# Source GitHub auth for push operations (worktree-aware)
if [[ -f "$PARENT_SCRIPT_DIR/github-auth.sh" ]]; then
    source "$PARENT_SCRIPT_DIR/github-auth.sh"
fi

#==============================================================================
# Lazy Command Loading
#==============================================================================

# Load a command module on demand
load_command() {
    local cmd=$1
    local cmd_file="$COMMANDS_DIR/${cmd}.sh"

    if [ -f "$cmd_file" ]; then
        source "$cmd_file"
        return 0
    else
        print_error "Command module not found: $cmd_file"
        return 1
    fi
}

#==============================================================================
# Main Command Router
#==============================================================================

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    stage|list|clear)
        load_command "stage"
        case "$COMMAND" in
            stage) tree_stage "$@" ;;
            list) tree_list "$@" ;;
            clear) tree_clear "$@" ;;
        esac
        ;;

    conflict|scope-conflicts)
        load_command "conflict"
        case "$COMMAND" in
            conflict) tree_conflict "$@" ;;
            scope-conflicts) tree_scope_conflicts "$@" ;;
        esac
        ;;

    build)
        load_command "build"
        tree_build "$@"
        ;;

    close)
        load_command "close"
        tree_close "$@"
        ;;

    status|restore|refresh)
        load_command "status"
        case "$COMMAND" in
            status) tree_status "$@" ;;
            restore) tree_restore "$@" ;;
            refresh) tree_refresh "$@" ;;
        esac
        ;;

    closedone)
        load_command "closedone"
        # Load stage for auto-staging incomplete features
        load_command "stage"
        closedone_main "$@"
        ;;

    help|--help|-h)
        load_command "help"
        tree_help
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        load_command "help"
        tree_help
        exit 1
        ;;
esac
