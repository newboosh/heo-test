---
title: Tree Worktree Management Command
type: reference
component: development-tools
created: 2024-10-15
updated: 2026-02-19
status: active
related:
  - scripts/tree.sh
  - docs/worktree-scope-detection.md
tags: [worktree, git, automation, development-workflow]
description: Manage git worktrees with intelligent automation for parallel development
---

Execute the tree worktree management script from this plugin.

**To execute:** Find this plugin's installation directory (the directory containing `.claude-plugin/plugin.json`), then run:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" <command> [args...]
```

Where `${PLUGIN_DIR}` is the heo plugin's installation path (e.g., `~/.claude/plugins/heo/` or wherever Claude Code installed this plugin).

## Basic Commands
- `/tree stage [description]` - Stage feature for worktree creation
- `/tree list` - Show staged features
- `/tree clear` - Clear all staged features
- `/tree conflict` - Analyze conflicts and suggest merges
- `/tree scope-conflicts` - Detect scope conflicts across worktrees
- `/tree build` - Create worktrees from staged features (auto-launches Claude)
- `/tree restore` - Restore terminals for existing worktrees
- `/tree status` - Show worktree environment status
- `/tree refresh` - Check slash command availability and get session reload guidance
- `/tree help` - Show detailed help

## Sync Commands
- `/tree sync` - Sync **current worktree only** from source/main (run from inside a worktree)
- `/tree sync --all` - Sync **all worktrees** from source/main (run from repo root)

**How sync works:**
1. Fetches `source/main` (falls back to `origin/main` if `source` not found)
2. Updates the local `main` ref
3. For each target worktree:
   - Reports untracked files, then stashes them alongside any tracked changes (`--include-untracked`)
   - Rebases the worktree branch onto `main` (linear history, no merge commits)
   - Pops the stash — restoring your in-progress work so you can review it against what came in from main
4. Detached HEAD worktrees are reported and skipped
5. If rebase fails, the stash is preserved — pop it manually after resolving conflicts

**Conflict resolution** — if rebase fails:
```bash
cd .trees/<worktree>
# fix conflicts, then:
git rebase --continue
# or to cancel:
git rebase --abort
```

## Cleanup Commands
- `/tree close` - Full worktree close: verify merge into remote main, run AI
  wrap-up phases (Remember, Learn, Publish), then remove worktree and delete
  local branch. Branch must be merged first or close will abort.
- `/tree close --force` - Skip merge verification (e.g., for abandoned branches).
  AI phases are still run; only the merge gate is bypassed.
- `/tree closedone` - Mechanical batch removal of all worktrees and branches
  (no AI phases). For the full wrap-up flow, use `/tree close` individually.
- `/tree closedone --dry-run` - Preview what would be removed

## Worktree Scope Detection

Each worktree automatically gets file boundary detection based on its feature description:

**How it works:**
1. `/tree build` analyzes feature descriptions for keywords (email, database, dashboard, etc.)
2. Generates `.worktree-scope.json` with file patterns for each worktree
3. Installs pre-commit hook to warn about out-of-scope changes
4. Creates special "librarian" worktree for documentation/tooling (inverse scope)

**Example:**
```bash
/tree stage Email OAuth refresh token implementation
/tree build

# Generated scope includes:
# - modules/email_integration/**
# - modules/email_integration/*oauth*.py
# - tests/test_*email_oauth_refresh*.py
```

**Enforcement modes:**
- **Soft (default)**: Warns but allows out-of-scope commits
- **Hard**: Blocks out-of-scope commits (edit `.worktree-scope.json`)
- **None**: Disables scope checking

**Librarian worktree:**
- Automatically created with inverse scope
- Works on docs, tooling, config files
- Excludes all files claimed by feature worktrees

For detailed documentation, see: `docs/worktree-scope-detection.md`

## Typical Workflow

```bash
# Stage features
/tree stage Add user authentication system
/tree stage Implement dashboard analytics
/tree build

# Work in worktrees...
# Commit, push, create PR on GitHub
# PR review with CodeRabbit + Claude
# Merge PR on GitHub

# Cleanup:
/tree close          # Full close: verify merge → AI phases → remove worktree
/tree closedone      # Mechanical batch cleanup (no AI phases)
```

**Note:** If `/tree` commands show "Unknown slash command" in worktrees:
- Run `/tree refresh` for diagnostics
- Workaround: Execute tree.sh directly from the plugin's scripts directory
- Permanent fix: Restart Claude Code CLI session from the worktree directory

For full documentation, see:
- Scope detection: `docs/worktree-scope-detection.md`
