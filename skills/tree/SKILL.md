---
description: Manage git worktrees with intelligent automation and full-cycle development workflows
---

# Tree Worktree Management

Execute the tree worktree management script located in this plugin's `scripts/tree.sh`.

## Script Location

The tree.sh script is bundled with this plugin at: `scripts/tree.sh` (relative to plugin root)

To execute, run:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" <command> [args...]
```

Where `${PLUGIN_DIR}` is the frosty plugin's installation directory (contains `.claude-plugin/plugin.json`).

## Commands

### Basic Commands
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

### Completion Commands
- `/tree close` - Complete feature and mark ready to merge
- `/tree close incomplete` - Save progress for continuation in next cycle
- `/tree closedone` - Batch merge and cleanup completed worktrees (includes log analysis)
- `/tree closedone --force` - Force merge all worktrees even if not closed
- `/tree closedone --full-cycle` - Complete entire development cycle automation

## Full-Cycle Automation

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
8. Analyzes git-orchestrator logs for merged branches

## Worktree Scope Detection

Each worktree automatically gets file boundary detection based on its feature description:

1. `/tree build` analyzes feature descriptions for keywords
2. Generates `.worktree-scope.json` with file patterns for each worktree
3. Installs pre-commit hook to warn about out-of-scope changes
4. Creates special "librarian" worktree for documentation/tooling

**Enforcement modes:**
- **Soft (default)**: Warns but allows out-of-scope commits
- **Hard**: Blocks out-of-scope commits
- **None**: Disables scope checking

## Example Workflow

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
```
