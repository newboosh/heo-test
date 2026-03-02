---
title: Tree Worktree Management Command
type: reference
component: development-tools
created: 2024-10-15
updated: 2026-02-20
status: active
related:
  - scripts/tree.sh
tags: [worktree, git, automation, development-workflow]
description: Manage git worktrees with intelligent automation for parallel development
help-usage: '`/tree stage <desc>`, `/tree list`, `/tree clear`, `/tree build`, `/tree sync [--all]`, `/tree status`, `/tree restore`, `/tree refresh`, `/tree conflict`, `/tree scope-conflicts`, `/tree help`'
help-extra-rows:
  - name: tree reset
    description: Complete task + reset
    usage: '`/tree reset`, `/tree reset incomplete`, `/tree reset --all [--force]`, `/tree reset --rename "name"`, `/tree reset --mechanical-only`, `/tree reset --force`'
  - name: tree closedone
    description: Remove all worktrees
    usage: '`/tree closedone [--dry-run]`'
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
   - Resets the worktree branch to `main` (`git reset --hard main`)
   - Pops the stash — restoring your in-progress work on top of main
4. Detached HEAD worktrees are reported and skipped
5. If reset fails, the stash is preserved — pop it manually after investigating

## Reset Commands
- `/tree reset` - Complete task: ship it → AI wrapup → mechanical reset (full 6-step orchestration)
- `/tree reset incomplete` - WIP save only: commit + push + synopsis (no wrapup, no reset)
- `/tree reset --all` - Batch mechanical reset of all worktrees (no AI phases)
- `/tree reset --all --force` - Batch reset discarding uncommitted changes
- `/tree reset --rename "new-task"` - Mechanical reset + rename branch for reuse
- `/tree reset --force` - Discard uncommitted changes, skip confirmations
- `/tree reset --mechanical-only` - Skip ship-it, just git reset (used internally by SKILL.md step 6)

**`/tree reset` 6-step sequence** (orchestrated by SKILL.md):
1. **Ship It** (bash) — auto-commit, push, synopsis, PR creation
2. **AI: Remember** — review work, persist knowledge to CLAUDE.md / rules / auto memory
3. **AI: Learn** — detect self-improvement patterns, auto-apply to main worktree
4. **Commit Learnings** (bash) — stage and commit learning files in main worktree
5. **AI: Publish** — review for publishable content, draft if warranted
6. **Mechanical Reset** (bash) — `git reset --hard origin/main` + `git clean -fd`

**When to use reset vs sync:**
- **After squash-merge PRs (full teardown):** Use `/tree reset` — ships the PR, runs AI wrapup phases, then resets the branch.
- **Mid-task, pull in latest main:** Use `/tree sync` — stashes WIP, resets branch to main, restores stash.

**When to use reset vs closedone:**
- **Same worktree, new task:** Use `/tree reset --rename "new-task"` — instant, preserves the worktree directory
- **Done with all worktrees:** Use `/tree closedone` — removes everything

## Cleanup Commands
- `/tree closedone` - Mechanical batch removal of all worktrees and branches
  (no AI phases). For the full wrap-up flow, use `/tree reset` individually.
- `/tree closedone --dry-run` - Preview what would be removed

## Deprecated Commands
- `/tree close` - **Deprecated.** Use `/tree reset` instead. Prints a deprecation warning and delegates to reset.

> **Important:** Remote branches must NOT be deleted after merge. They serve as historical references for traceability and rollbacks. Only local branches and worktrees should be cleaned up.

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

# After task complete — full reset with AI wrapup:
/tree reset              # Ship It → Remember → Learn → Publish → Mechanical Reset

# Or save WIP and come back later:
/tree reset incomplete   # Commit + push only, no wrapup

# Or batch reset all worktrees mechanically:
/tree reset --all        # git reset --hard all worktrees

# Sync during active development (reset branch to latest main):
/tree sync               # Reset onto latest main

# Batch cleanup:
/tree closedone          # Remove all worktrees at once
```

**Note:** If `/tree` commands show "Unknown slash command" in worktrees:
- Run `/tree refresh` for diagnostics
- Workaround: Execute tree.sh directly from the plugin's scripts directory
- Permanent fix: Restart Claude Code CLI session from the worktree directory

