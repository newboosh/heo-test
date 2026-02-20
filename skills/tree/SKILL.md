---
name: tree
description: Manage git worktrees with intelligent automation for parallel development
model: sonnet
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Tree Worktree Management

Execute the tree worktree management script located in this plugin's `scripts/tree.sh`.

## Script Location

The tree.sh script is bundled with this plugin at: `scripts/tree.sh` (relative to plugin root)

To execute, run:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" <command> [args...]
```

Where `${PLUGIN_DIR}` is the heo plugin's installation directory (contains `.claude-plugin/plugin.json`).

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

### Cleanup Commands
- `/tree close` - Verify merge, run AI wrap-up phases, then remove worktree
- `/tree close --force` - Skip merge verification (e.g., for abandoned branches)
- `/tree closedone` - Mechanical batch removal of all worktrees (no AI phases)
- `/tree closedone --dry-run` - Preview what would be removed

## `/tree close` — Full Worktree Close

When the user invokes `/tree close`, follow this sequence exactly:

### Step 1: Merge Verification

Run the merge check:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" close --check-only
```

If the script exits non-zero (branch not merged), stop. The script already
printed the warning — do not proceed further.

If the script exits zero (branch is merged), continue to the AI phases below.

Also capture the **main worktree path** and **worktree name** for later use:
```bash
MAIN_WORKTREE=$(git worktree list --porcelain | head -1 | sed 's/^worktree //')
WORKTREE_NAME=$(basename "$(git rev-parse --show-toplevel)")
```

### Step 2: AI Phase 1 — Remember

Review what was learned during this worktree's work. Gather context by
examining the worktree's git log (`git log main..HEAD --oneline`), diffs,
and any notable files.

Decide where each piece of knowledge belongs in the memory hierarchy:

- **Auto memory** — Debugging insights, patterns discovered, project quirks.
  Write directly to the auto memory directory (outside git, no commit needed).
- **CLAUDE.md** — Permanent project rules, conventions, architecture decisions
  that should guide all future sessions. Edit in the **main worktree**
  (`${MAIN_WORKTREE}/CLAUDE.md`), not the feature worktree.
- **`.claude/rules/`** — Topic-specific modular rules. Use `paths:` frontmatter
  to scope rules to relevant files. Write to `${MAIN_WORKTREE}/.claude/rules/`.
- **`CLAUDE.local.md`** — Personal WIP context, local URLs, sandbox credentials,
  current focus areas that shouldn't be committed.
- **`@import` references** — When a CLAUDE.md would benefit from referencing
  another file rather than duplicating its content.

**Decision framework:**
- Permanent project convention? → CLAUDE.md or `.claude/rules/`
- Scoped to specific file types? → `.claude/rules/` with `paths:` frontmatter
- Pattern or insight Claude discovered? → Auto memory
- Personal/ephemeral context? → `CLAUDE.local.md`
- Duplicating content from another file? → Use `@import` instead

### Step 3: AI Phase 2 — Learn

Analyze the worktree's work for self-improvement findings. If the work was
routine with nothing notable, say "Nothing to improve" and skip to Step 5.

**Auto-apply all actionable findings immediately** — do not ask for approval.
Apply changes to the **main worktree** (not the feature worktree). Then present
a summary.

**Pattern types to detect:**
- `error_resolution` — How specific errors were resolved
- `user_corrections` — Patterns from user corrections
- `workarounds` — Solutions to framework quirks
- `debugging_techniques` — Effective debugging approaches
- `skill_gaps` — Things Claude struggled with or got wrong
- `friction` — Repeated manual steps that should be automatic
- `automation` — Repetitive patterns that could become skills, hooks, or scripts

**Action types:**
- **CLAUDE.md** — Edit at `${MAIN_WORKTREE}/CLAUDE.md`
- **`.claude/rules/`** — Create or update at `${MAIN_WORKTREE}/.claude/rules/`
- **Auto memory** — Save insights for future sessions (outside git)
- **Skill / Hook spec** — Document a new skill or hook for implementation
- **`.claude/skills/learned/`** — Save structured learned skills at
  `${MAIN_WORKTREE}/.claude/skills/learned/`

Present findings in two sections — applied items first, then no-action items:

```text
Findings (applied):

1. Skill gap: Cost estimates were wrong multiple times
   → [CLAUDE.md] Added token counting reference table

2. Automation: Checking service health after deploy is manual
   → [Skill] Created post-deploy health check skill spec

---
No action needed:

3. Knowledge: Discovered X works this way
   Already documented in CLAUDE.md
```

### Step 4: Commit Learnings

Commit only the learning-related files that were modified in the main worktree.
Do **not** use `git add -A`. Stage specific paths only:

```bash
cd "${MAIN_WORKTREE}"
git add CLAUDE.md CLAUDE.local.md .claude/rules/ .claude/skills/learned/ 2>/dev/null
git diff --cached --quiet || git commit -m "chore: apply learnings from worktree close (${WORKTREE_NAME})"
git push
```

If there are no staged changes, skip this step. Auto memory files are outside
the git repo and need no commit.

### Step 5: AI Phase 3 — Publish

Review the work done in this worktree for publishable material. Look for:

- Interesting technical solutions or debugging stories
- Community-relevant announcements or updates
- Educational content (how-tos, tips, lessons learned)
- Project milestones or feature launches

**If publishable material exists:**

1. From the main worktree, create or switch to the `content/drafts` branch:
   ```bash
   cd "${MAIN_WORKTREE}"
   git checkout -B content/drafts origin/content/drafts 2>/dev/null || git checkout -b content/drafts
   ```
2. Draft the article(s) and save to a `Drafts/` folder.
3. Commit and push the drafts (this branch has no CodeRabbit review):
   ```bash
   git add Drafts/
   git commit -m "content: draft from ${WORKTREE_NAME} worktree"
   git push -u origin content/drafts
   ```
4. Switch back to main:
   ```bash
   git checkout main
   ```

**If no publishable material exists:**
Say "Nothing worth publishing from this worktree" and move on.

### Step 6: Mechanical Close

Run the close script with `--force` to skip the redundant merge re-check:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" close --force
```

This removes the worktree directory and deletes the local branch.

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

# Full close (with AI wrap-up):
/tree close          # Verify merge → Remember → Learn → Publish → Remove

# Batch mechanical cleanup (no AI phases):
/tree closedone      # Remove all worktrees at once
```
