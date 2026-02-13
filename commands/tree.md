---
title: Tree Worktree Management Command
type: reference
component: development-tools
created: 2024-10-15
updated: 2025-10-30
status: active
related:
  - scripts/tree.sh
  - docs/worktree-scope-detection.md
  - tasks/tree-workflow-full-cycle/prd.md
tags: [worktree, git, automation, development-workflow]
description: Manage git worktrees with intelligent automation and full-cycle development workflows
---

Execute the tree worktree management script from this plugin.

**To execute:** Find this plugin's installation directory (the directory containing `.claude-plugin/plugin.json`), then run:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" <command> [args...]
```

Where `${PLUGIN_DIR}` is the frosty plugin's installation path (e.g., `~/.claude/plugins/frosty/` or wherever Claude Code installed this plugin).

This command provides comprehensive worktree management with full development cycle automation:

## Basic Commands
- `/tree stage [description]` - Stage feature for worktree creation
- `/tree list` - Show staged features
- `/tree clear` - Clear all staged features
- `/tree conflict` - Analyze conflicts and suggest merges
- `/tree scope-conflicts` - Detect scope conflicts across worktrees (NEW)
- `/tree build` - Create worktrees from staged features (auto-launches Claude)
- `/tree restore` - Restore terminals for existing worktrees
- `/tree status` - Show worktree environment status
- `/tree refresh` - Check slash command availability and get session reload guidance
- `/tree help` - Show detailed help

## Completion Commands
- `/tree close` - Complete feature and mark ready to merge
- `/tree close incomplete` - Save progress for continuation in next cycle (NEW)
- `/tree closedone` - Batch merge and cleanup completed worktrees (includes log analysis)
- `/tree closedone --force` - Force merge all worktrees even if not closed (NEW)
- `/tree closedone --full-cycle` - Complete entire development cycle automation (NEW)

**Note:** Both `/tree closedone` commands automatically analyze git-orchestrator logs for merged branches to identify patterns and issues.

## Important: Worktree Validation

**New Behavior:** `/tree closedone` now validates that all worktrees have been properly closed with `/tree close` before merging. This ensures:
- All work is documented with synopsis files
- No accidental merges of incomplete work
- Better tracking of what was accomplished

If you have unclosed worktrees, you'll see a summary like:
```
⚠️  Cannot proceed: 3 worktree(s) have not been closed

The following worktrees need to be closed with '/tree close' before merging:

  • feature-name-1
    Branch: task/01-feature-name-1
    Path: /workspace/.trees/feature-name-1

Options:
  1. Close each worktree: cd .trees/<worktree> && /tree close
  2. Use --force to merge all worktrees anyway: /tree closedone --force
```

**Use `--force` to bypass validation** if you want to merge everything regardless of close status.

## Full-Cycle Automation

The `--full-cycle` flag automates the complete development lifecycle:

```bash
/tree closedone --full-cycle [--bump patch|minor|major] [--dry-run] [--yes]
```

**What it does:**
1. Validates all worktrees are closed
2. Merges completed features to development branch
3. Promotes development branch to main
4. Bumps version (patch by default)
5. Creates new development branch
6. Auto-stages incomplete features for next cycle
7. Archives synopses and generates report
8. **Analyzes git-orchestrator logs for merged branches**

**Options:**
- `--bump [type]` - Version bump type: patch (default), minor, or major
- `--yes` - (Legacy - kept for compatibility, no longer needed)

**Note:** Confirmation prompts have been removed for faster workflow. All operations proceed automatically.

**Example workflow:**
```bash
# Stage features
/tree stage Add user authentication system
/tree stage Implement dashboard analytics
/tree build

# Work in worktrees...
# In worktree A: /tree close              # Feature complete
# In worktree B: /tree close incomplete   # Need more work

# Back in main workspace:
/tree closedone --full-cycle --bump minor

# Result:
# - Completed feature merged to main
# - Version bumped from 4.3.2 → 4.4.0
# - New dev branch: develop/v4.4.0-worktrees-20251012-120000
# - Incomplete feature auto-staged for next cycle
```

## Incomplete Features

Use `/tree close incomplete` to mark features that need to continue in the next development cycle:

```bash
# In worktree
cd /workspace/.trees/my-feature
/tree close incomplete

# This feature will automatically be staged when running:
/tree closedone --full-cycle
```

## Worktree Scope Detection (NEW)

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

**Note:** If `/tree` commands show "Unknown slash command" in worktrees:
- Run `/tree refresh` for diagnostics
- Workaround: Execute tree.sh directly from the plugin's scripts directory
- Permanent fix: Restart Claude Code CLI session from the worktree directory

For full documentation, see:
- Full-cycle workflow: `tasks/tree-workflow-full-cycle/prd.md`
- Scope detection: `docs/worktree-scope-detection.md`

