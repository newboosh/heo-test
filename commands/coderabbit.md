# CodeRabbit Review Management

Orchestrate a single iteration of CodeRabbit PR review processing.

## Overview

This command orchestrates three subcommands to process CodeRabbit reviews:

```
/coderabbit
    │
    ├─► /coderabbit status     → Check PR state
    │   │
    │   ├─► REVIEWING → Stop, wait for review
    │   ├─► CLEAN → Stop, PR is ready
    │   └─► COMMENTS/CONFLICTS → Continue
    │
    ├─► /coderabbit process    → Fix comments, push
    │   (if comments exist)
    │
    └─► /coderabbit conflicts  → Resolve conflicts, push
        (if conflicts exist)
```

## Subcommands

| Command | Purpose |
|---------|---------|
| `/coderabbit status` | Check PR status (reviewing, comments, conflicts, clean) |
| `/coderabbit process` | Fetch comments, apply fixes, commit and push |
| `/coderabbit conflicts` | Resolve merge conflicts, commit and push |

## Prerequisites

**GitHub Token**: Required for accessing PR comments. Loaded from:
1. `GITHUB_TOKEN` environment variable
2. Repository root `.env` file (`GITHUB_TOKEN=<token>` or `GITHUB_PAT=<token>`)

## Arguments

- `$ARGUMENTS` - Optional flags and PR number:
  - `<PR_NUMBER>` - PR to process (default: detect from current branch)
  - `--no-resolve` - Don't auto-resolve comments (let CodeRabbit verify)
  - `--no-push` - Don't commit/push changes (for dry-run inspection)
  - `--iteration <N>` - Current iteration number (for commit messages)
  - `status` - Only check status (calls `/coderabbit status`)
  - `process` - Only process comments (calls `/coderabbit process`)
  - `conflicts` - Only resolve conflicts (calls `/coderabbit conflicts`)

## Instructions

**You are orchestrating a CodeRabbit review iteration.**

---

### Step 1: Check Status

Delegate to `/coderabbit status`:

```
/coderabbit status $PR_NUMBER
```

Based on the result:

| Status | Action |
|--------|--------|
| **REVIEWING** | **STOP** - Report "Review in progress" |
| **CLEAN** | **STOP** - Report "PR is clean" |
| **COMMENTS** | Go to Step 2 |
| **CONFLICTS_BLOCKED** | Go to Step 2, then Step 3 |
| **CONFLICTS_ONLY** | Skip to Step 3 |

---

### Step 2: Process Comments

Delegate to `/coderabbit process`:

```
/coderabbit process $PR_NUMBER --iteration $N
```

Pass through flags: `--no-resolve`, `--no-push`

**CRITICAL: Fixes MUST be pushed BEFORE resolving conflicts.** Resolving conflicts triggers a full re-review.

---

### Step 3: Resolve Conflicts (if any)

**Skip if no conflicts or `--no-push` flag is set.**

Delegate to `/coderabbit conflicts`:

```
/coderabbit conflicts $PR_NUMBER
```

---

### Step 4: Report Results

Output a summary:
- PR status
- Comments processed
- Conflicts resolved
- Final state

---

## Important Rules

- **Push fixes BEFORE resolving conflicts** - Fixes must be committed and pushed first, then conflicts resolved in a separate commit
- **Never auto-resolve security comments** without manual verification
- **Always run quality checks** before pushing
- **Reference Dignified Python rules** when explaining fixes (e.g., "Fixed per Rule #2")
- **Use `@coderabbitai` mentions** to communicate with CodeRabbit

## Error Handling

Errors from subcommands bubble up. See individual subcommand documentation:
- `/coderabbit process` - Quality check failures, comment processing failures
- `/coderabbit conflicts` - Conflict resolution failures, push failures

## Composition

This command follows the **Composition Pattern** (see `/composition-patterns`):

```
/coderabbit (orchestrator)
    ├─► /coderabbit status   (Gate pattern - determines workflow)
    ├─► /coderabbit process  (Delegation pattern)
    └─► /coderabbit conflicts (Delegation pattern)
```

Each subcommand is independently useful and testable.
