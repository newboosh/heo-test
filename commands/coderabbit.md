# CodeRabbit Review Management

Run a single iteration of CodeRabbit PR review processing: check status, fix comments, resolve conflicts.

For a full loop that repeats until approval, use `/coderabbitloop`.

## Arguments

- `$ARGUMENTS` - Optional flags and PR number:
  - `<PR_NUMBER>` - PR to process (default: detect from current branch)
  - `--no-resolve` - Don't auto-resolve comments (let CodeRabbit verify)
  - `--no-push` - Don't commit/push changes (for dry-run inspection)
  - `--iteration <N>` - Current iteration number (for commit messages)

## Prerequisites

**GitHub Token**: Required for accessing PR comments. Loaded from:
1. `GITHUB_TOKEN` environment variable
2. Repository root `.env` file (`GITHUB_TOKEN=<token>` or `GITHUB_PAT=<token>`)

## Instructions

**You are running a single CodeRabbit review iteration.**

---

### Step 1: Identify the PR

If no PR number was provided:
```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
```

---

### Step 2: Check Status

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/check_pr_status.py" --pr $PR_NUMBER --json
```

Based on the result:

| State | Condition | Action |
|-------|-----------|--------|
| **REVIEWING** | CodeRabbit review in progress | **STOP** — Report "Review in progress, try again later" |
| **CLEAN** | No unresolved comments, no conflicts | **STOP** — Report "PR is clean" |
| **MERGED** | PR was merged | **STOP** — Report success |
| **COMMENTS** | Has unresolved comments | Go to Step 3 |
| **CONFLICTS_BLOCKED** | Has both comments and conflicts | Go to Step 3, then Step 4 |
| **CONFLICTS_ONLY** | Has conflicts, no comments | Skip to Step 4 |

---

### Step 3: Process Comments

#### 3a. Fetch all unresolved comments

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/fetch_comments.py" --pr $PR_NUMBER --json
```

Also fetch outside-diff comments:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/fetch_outside_diff_comments.py" --pr $PR_NUMBER
```

#### 3b. For each comment, apply fixes

1. **Read the file** at the specified location
2. **If CodeRabbit provides a committable suggestion** — apply it EXACTLY
3. **If no suggestion** — create a minimal fix
4. **Verify locally**:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh
   ```
   Max 3 attempts per comment. After 3 failures, escalate.

#### 3c. Post replies

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/post_reply.py" --pr $PR_NUMBER --thread <THREAD_ID> --body "<REPLY>"
```

#### 3d. Auto-resolve (unless `--no-resolve`)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/smart_resolver.py" --pr $PR_NUMBER
```

#### 3e. Commit and push

Stage, commit, and push via `/push`.

**CRITICAL: Push fixes BEFORE resolving conflicts.**

---

### Step 4: Resolve Conflicts (if any)

**Skip if no conflicts or `--no-push`.**

```bash
git fetch origin main
git merge origin/main
```

Resolve each conflict intelligently, run quality checks, commit and push via `/push`.

---

### Step 5: Report Results

Output a summary:
- PR status
- Comments processed and files modified
- Conflicts resolved
- Final state
- Suggest `/coderabbitloop` if there are more iterations needed

## Important Rules

- **Push fixes BEFORE resolving conflicts** — conflict resolution triggers re-review
- **Never auto-resolve security comments** without manual verification
- **Always run quality checks** before pushing
- **Use CodeRabbit's exact suggestions** when provided
- **Max 3 attempts per comment** — escalate after 3 failures
