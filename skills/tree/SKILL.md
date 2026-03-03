---
name: tree
description: Manage git worktrees with intelligent automation for parallel development
model: sonnet
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Tree Worktree Management

## CRITICAL: Execution Rules

**Execute ONLY the exact command the user requested.** Do not:
- Remove, clean up, or modify worktrees unless the user explicitly invokes `/tree reset`, `/tree closedone`, etc.
- Add "helpful" pre-steps like cleaning up old worktrees before staging
- Reorganize, rename, or consolidate worktrees without being asked
- Take any action beyond running the requested bash command and reporting its output

If the user runs `/tree stage login page not working`, execute:
```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" stage login page not working
```
Nothing more. Do not "prepare" the environment first.

---

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
- `/tree build` - Create worktrees from staged features
- `/tree status` - Show worktree environment status
- `/tree refresh` - Check slash command availability and get session reload guidance
- `/tree help` - Show detailed help

### Sync Commands
- `/tree sync` - Sync current worktree from source/main via rebase
- `/tree sync --all` - Sync all worktrees from source/main via rebase

### Reset Commands
- `/tree reset` - Complete task: ship it → AI wrapup → mechanical reset (orchestrated below)
- `/tree reset incomplete` - WIP save only: commit + push + synopsis (no wrapup, no reset)
- `/tree reset --all` - Batch mechanical reset of all worktrees (no AI phases)
- `/tree reset --all --force` - Batch reset discarding uncommitted changes
- `/tree reset --rename "new-task"` - Mechanical reset + rename branch for reuse
- `/tree reset --mechanical-only` - Skip ship-it, just git reset (used internally by step 6)

### Cleanup Commands
- `/tree closedone` - Mechanical batch removal of all worktrees (no AI phases)
- `/tree closedone --dry-run` - Preview what would be removed

### Deprecated
- `/tree close` - **Deprecated.** Use `/tree reset` instead.

---

## `/tree reset` — Full Orchestration (Single Worktree)

When the user invokes `/tree reset` (without `--all`, `incomplete`, or `--mechanical-only`),
follow this **6-step sequence exactly**:

### Step 1: Ship It (bash)

Run the reset script to auto-commit, push, generate synopsis, and offer PR creation:

```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" reset
```

This runs `tree_reset_ship_it()` which:
- Detects the worktree (must be inside `.trees/`)
- Auto-commits all uncommitted changes
- Pushes branch to origin
- Generates synopsis to `.trees/.completed/`
- Offers to create PR via `gh`

After this command completes, capture context for the AI phases:
```bash
MAIN_WORKTREE=$(git worktree list --porcelain | head -1 | sed 's/^worktree //')
WORKTREE_NAME=$(basename "$(git rev-parse --show-toplevel)")
```

### Step 2: AI Phase — Remember

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

### Step 3: AI Phase — Learn

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

### Step 4: Commit Learnings (bash)

Commit only the learning-related files that were modified in the main worktree.
Do **not** use `git add -A`. Stage specific paths only:

```bash
cd "${MAIN_WORKTREE}"
git add CLAUDE.md CLAUDE.local.md .claude/rules/ .claude/skills/learned/ 2>/dev/null
git diff --cached --quiet || git commit -m "chore: apply learnings from worktree reset (${WORKTREE_NAME})"
git push
```

If there are no staged changes, skip this step. Auto memory files are outside
the git repo and need no commit.

### Step 5: AI Phase — Publish

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

### Step 6: Mechanical Reset (bash)

Run the reset script with `--mechanical-only` to perform the actual git reset:

```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" reset --mechanical-only --force
```

This performs `git reset --hard origin/main` + `git clean -fd`, making the
worktree fresh and ready for a new task.

---

## `/tree reset --all` — Batch Mechanical Reset

Just call the bash script directly (mechanical only, no AI phases):

```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" reset --all [--force]
```

## `/tree reset incomplete` — WIP Save

Just call the bash script directly (commit + push + incomplete synopsis, no wrapup, no reset):

```bash
bash "${PLUGIN_DIR}/scripts/tree.sh" reset incomplete
```

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

# Or reset + rename for reuse:
/tree reset --rename "new-feature-name"

# Sync during active development:
/tree sync               # Rebase onto latest main

# Batch cleanup (after GitHub PR merges):
/tree closedone          # Remove all worktrees at once
```
