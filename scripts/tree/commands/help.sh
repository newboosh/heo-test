#!/bin/bash
#
# Script: commands/help.sh
# Purpose: Help command for tree worktree system
# Created: 2026-01-28
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
  scope-conflicts        - Detect scope conflicts across worktrees
  build [options]        - Create worktrees from staged features
  restore                - Restore terminals for existing worktrees
  close                  - Remove the current worktree
  closedone              - Prune all local worktrees
  sync [--all]           - Sync worktree(s) from source/main via rebase
  status                 - Show worktree environment status
  refresh                - Check slash command availability
  help                   - Show this help

/tree build options:
  --resume               Resume incomplete build
  --verbose, -v          Show detailed output
  --confirm              Prompt before each worktree
  --dry-run              Preview without creating

/tree sync usage:
  /tree sync               Sync current worktree from source/main (run from inside a worktree)
  /tree sync --all         Sync all worktrees from source/main (run from repo root)

  Stashes all changes (including untracked files) before rebasing onto main,
  then pops the stash so you can review your work against what changed in main.

/tree close usage:
  /tree close

  Removes the current worktree and deletes the local branch.
  Warns if there are uncommitted changes.

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
  5. [commit, push, create PR]  # Ship via GitHub
  6. [PR review on GitHub]      # Code review
  7. [Merge PRs on GitHub]      # Merge via GitHub
  8. /tree close                # Remove finished worktree
  9. /tree closedone            # Or prune all at once

Examples:
  /tree stage Add user preferences backend
  /tree stage Dashboard analytics view
  /tree list
  /tree build --dry-run          # Preview
  /tree build                    # Create worktrees
  /tree build --resume           # Resume after failure
  /tree close                    # Remove current worktree
  /tree closedone                # Prune all worktrees
  /tree closedone --dry-run      # Preview pruning

EOF
}
