#!/bin/bash
#
# Script: commands/help.sh
# Purpose: Help command for tree worktree system
# Created: 2026-01-28
# Modified: 2026-02-20
# Description: Display help and usage information

# /tree help
tree_help() {
    cat << 'EOF'
Tree Worktree Management

Available commands:
  stage [description]    - Stage feature for worktree creation
  list                   - Show staged features
  clear                  - Clear all staged features
  conflict               - Analyze conflicts and suggest merges
  build [options]        - Create worktrees from staged features
  restore                - Restore terminals for existing worktrees
  sync [--all]           - Sync worktree(s) from origin/main via rebase
  reset [options]        - Complete task: ship it, AI wrapup, reset
  closedone              - Prune all local worktrees
  status                 - Show worktree environment status
  refresh                - Check slash command availability
  help                   - Show this help

/tree build options:
  --resume               Resume incomplete build
  --verbose, -v          Show detailed output
  --confirm              Prompt before each worktree
  --dry-run              Preview without creating

/tree sync usage:
  /tree sync               Sync current worktree from origin/main (run from inside a worktree)
  /tree sync --all         Sync all worktrees from origin/main (run from repo root)

  Stashes all changes (including untracked files) before rebasing onto main,
  then pops the stash so you can review your work against what changed in main.

/tree reset usage:
  /tree reset              Full task completion (ship it -> AI wrapup -> reset)
  /tree reset incomplete   Save WIP (commit + push only, no wrapup, no reset)
  /tree reset --all        Batch mechanical reset of all worktrees
  /tree reset --force      Discard uncommitted changes, skip confirmations
  /tree reset --rename X   Rename branch after mechanical reset
  /tree reset --mechanical-only  Skip ship-it, just git reset (used by SKILL.md)

  SHIP IT: /tree reset automatically:
     1. Commits all uncommitted changes
     2. Pushes branch to origin
     3. Generates synopsis
     4. Offers to create PR via gh CLI
  Then SKILL.md orchestrates AI wrapup phases (Remember, Learn, Publish)
  and finally performs the mechanical git reset.

/tree closedone usage:
  /tree closedone [--dry-run]

  Removes all local worktrees and cleans up local branches.
  Remote branches are preserved. Use --dry-run to preview.

Environment Variables:
  TREE_VERBOSE=true      Enable verbose mode globally
  TREE_NON_INTERACTIVE=1 Disable prompts (CI mode)

Typical Workflow:
  1. /tree stage [description]  # Stage features
  2. /tree list                 # Review staged
  3. /tree build                # Create worktrees
  4. [work in worktrees]        # Implement
  5. /tree reset                # Ship it + AI wrapup + reset
  6. [PR review on GitHub]      # Code review
  7. [Merge PRs on GitHub]      # Merge via GitHub
  8. /tree closedone            # Prune local worktrees

Deprecated:
  /tree close              Use '/tree reset' instead

Examples:
  /tree stage Add user preferences backend
  /tree stage Dashboard analytics view
  /tree list
  /tree build --dry-run          # Preview
  /tree build                    # Create worktrees
  /tree build --resume           # Resume after failure
  /tree sync                     # Sync current worktree
  /tree reset                    # Full task completion
  /tree reset incomplete         # Save WIP progress
  /tree reset --all --force      # Batch reset all worktrees
  /tree closedone                # Prune all worktrees
  /tree closedone --dry-run      # Preview pruning

EOF
}
