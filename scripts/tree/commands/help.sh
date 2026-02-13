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
  close [incomplete]     - Commit, push to remote, create PR
  closedone              - Prune local worktrees (after GitHub PR merge)
  status                 - Show worktree environment status
  refresh                - Check slash command availability
  help                   - Show this help

/tree build options:
  --resume               Resume incomplete build
  --verbose, -v          Show detailed output
  --confirm              Prompt before each worktree
  --dry-run              Preview without creating

/tree close usage:
  /tree close              Complete feature and create PR
  /tree close incomplete   Save progress for next cycle

  AUTO-COMMIT + PUSH: /tree close automatically:
     1. Commits all uncommitted changes
     2. Pushes branch to origin
     3. Offers to create PR via gh CLI

/tree closedone usage:
  /tree closedone [options]

  Prunes local worktrees after PRs merged on GitHub.
  NOTE: Merging happens via GitHub PRs, NOT locally.

Options:
  --force                Prune regardless of close status
  --dry-run              Preview without pruning

/tree closedone --full-cycle usage:
  /tree closedone --full-cycle [--bump patch|minor|major] [--dry-run]

  Executes complete development cycle:
  1. Validate all worktrees closed
  2. Merge completed features
  3. Promote to main
  4. Bump version
  5. Create new dev branch
  6. Auto-stage incomplete features

Environment Variables:
  TREE_VERBOSE=true      Enable verbose mode globally
  TREE_NON_INTERACTIVE=1 Disable prompts (CI mode)

Typical Workflow:
  1. /tree stage [description]  # Stage features
  2. /tree list                 # Review staged
  3. /tree build                # Create worktrees
  4. [work in worktrees]        # Implement
  5. /tree close                # Commit, push, PR
  6. [PR review on GitHub]      # Code review
  7. [Merge PRs on GitHub]      # Merge via GitHub
  8. /tree closedone            # Prune local worktrees

Examples:
  /tree stage Add user preferences backend
  /tree stage Dashboard analytics view
  /tree list
  /tree build --dry-run          # Preview
  /tree build                    # Create worktrees
  /tree build --resume           # Resume after failure
  /tree close                    # Complete feature
  /tree close incomplete         # Save progress
  /tree closedone                # Prune completed
  /tree closedone --full-cycle   # Full cycle automation

EOF
}
