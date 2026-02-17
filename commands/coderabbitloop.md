# CodeRabbit Loop

Loop on a PR until CodeRabbit approves all changes. Automatically checks status, fixes comments, resolves conflicts, pushes, and waits for re-review — repeating until the PR is clean or max iterations (8) are reached.

## Arguments

- `$ARGUMENTS` - Optional PR number and flags:
  - `<PR_NUMBER>` - PR to process (default: detect from current branch)
  - `--no-resolve` - Don't auto-resolve comments (let CodeRabbit verify)
  - `--max-iterations <N>` - Override max iterations (default: 8)

## Prerequisites

**GitHub Token**: Required for accessing PR comments. Loaded from:
1. `GITHUB_TOKEN` environment variable
2. Repository root `.env` file (`GITHUB_TOKEN=<token>` or `GITHUB_PAT=<token>`)

## Instructions

**You are running a CodeRabbit review loop. You will iterate until the PR is clean or you hit max iterations.**

---

### Identify the PR

If no PR number was provided:
```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
```

Report error and stop if no PR is found.

---

### The Loop

Set `ITERATION=1` and `MAX_ITERATIONS=8` (or override from args). Then repeat:

#### Step 1: Check Status

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/check_pr_status.py" --pr $PR_NUMBER --json
```

Parse the result and determine the state:

| State | Condition | Action |
|-------|-----------|--------|
| **REVIEWING** | CodeRabbit review in progress | **WAIT** — sleep 60 seconds, re-check (up to 15 times) |
| **CLEAN** | No unresolved comments, no conflicts | **STOP — SUCCESS** |
| **MERGED** | PR was merged | **STOP — SUCCESS** |
| **CLOSED** | PR was closed without merge | **STOP — report closure** |
| **COMMENTS** | Has unresolved comments | Go to Step 2 |
| **CONFLICTS_BLOCKED** | Has both comments and conflicts | Go to Step 2, then Step 3 |
| **CONFLICTS_ONLY** | Has conflicts, no comments | Skip to Step 3 |

If REVIEWING, wait and re-check:
```bash
sleep 60
```
Re-run the status check. If still REVIEWING after 15 waits (15 minutes), report "CodeRabbit is still reviewing — try again later" and stop.

---

#### Step 2: Process Comments

##### 2a. Fetch all unresolved comments

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/fetch_comments.py" --pr $PR_NUMBER --json
```

Also fetch outside-diff comments:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/fetch_outside_diff_comments.py" --pr $PR_NUMBER
```

##### 2b. For each comment, apply fixes

For each inline comment:
1. **Read the file** at the specified location
2. **If CodeRabbit provides a committable suggestion** — apply it EXACTLY as provided. Do NOT modify or "improve" the suggestion.
3. **If no suggestion** — parse the rule reference, understand what's requested, create a minimal fix
4. **Apply the fix** using the Edit tool
5. **Verify locally** — run quality checks:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh
   ```
   If quality fails, iterate on the fix (max 3 attempts per comment). After 3 failures, escalate.

For each general comment with file references, apply the same process.

##### 2c. Post replies

For each fixed comment:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/loop/post_reply.py" --pr $PR_NUMBER --thread <THREAD_ID> --body "<REPLY>"
```

Reply format:
```
@coderabbitai

**Fix applied** at `file.py:line`

[Description of change]

**Verification:** Quality checks passed

Please verify and resolve this thread.
```

##### 2d. Auto-resolve comments (unless `--no-resolve`)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/smart_resolver.py" --pr $PR_NUMBER
```

Security comments are never auto-resolved.

##### 2e. Commit and push fixes

Stage changed files and commit:
```bash
git add <files that were changed>
```

```bash
git commit -m "$(cat <<'EOF'
fix: address CodeRabbit review comments (iteration N/8)

- <summary of fix 1>
- <summary of fix 2>

PR: #$PR_NUMBER

Co-Authored-By: Steve Glen <therealstevenglen@gmail.com>
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Push via `/push`.

**CRITICAL: Fixes MUST be pushed BEFORE resolving conflicts.** Resolving conflicts triggers a full re-review.

---

#### Step 3: Resolve Conflicts (if any)

**Skip if no conflicts.**

```bash
git fetch origin main
git merge origin/main
```

If no conflicts, skip to Step 4.

For each conflicted file:
1. Review the conflict markers
2. Make intelligent merge decisions (prefer keeping both changes when possible)
3. Verify the resolution is syntactically valid

After resolving:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh
```

Commit and push:
```bash
git add <resolved files>
```

```bash
git commit -m "$(cat <<'EOF'
fix(merge): resolve conflicts with main (iteration N/8)

Resolved conflicts in:
- <file1>
- <file2>

Co-Authored-By: Steve Glen <therealstevenglen@gmail.com>
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Push via `/push`.

---

#### Step 4: Wait for CodeRabbit Re-review

After pushing fixes or conflict resolutions, CodeRabbit will re-review. You **MUST** confirm CodeRabbit has reviewed the new push before accepting a CLEAN result.

**Phase 1 — Wait for review to start:**

Poll every 30 seconds for up to 5 minutes. Run the status check each time:
```bash
sleep 30
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/coderabbit/check_pr_status.py" --pr $PR_NUMBER --json
```

You are waiting for the status to show **REVIEWING** (SKIP state), which means CodeRabbit picked up the new push. Once REVIEWING is detected, move to Phase 2.

If REVIEWING is never detected within 5 minutes (10 polls), move to Phase 2 anyway — CodeRabbit may have reviewed very quickly.

**Phase 2 — Wait for review to finish:**

Now use the same REVIEWING wait logic from Step 1: poll every 60 seconds for up to 15 minutes until the status is no longer REVIEWING.

**Then increment ITERATION and go back to Step 1.**

> **CRITICAL:** Do NOT accept a CLEAN status in Step 1 on the first check after a push. If Step 1 returns CLEAN immediately and Phase 1 never detected REVIEWING, wait 60 seconds and re-check once more to guard against the race condition where CodeRabbit hasn't started yet.

---

### Exit Conditions

The loop stops when:

| Condition | Result |
|-----------|--------|
| PR is **CLEAN** (no comments, no conflicts) | Report success |
| PR is **MERGED** | Report success |
| PR is **CLOSED** | Report closure |
| **Max iterations** reached | Report what's still unresolved |
| **Rate limited** | Report and suggest retry later |
| **Unrecoverable error** | Report the error |

---

### Final Summary

When the loop ends, output:

```
## CodeRabbit Loop Complete

PR: #123
Iterations: 3/8
Final state: CLEAN

### Changes made:
- Iteration 1: Fixed 4 comments (auth.py, utils.py)
- Iteration 2: Fixed 2 comments (models.py), resolved merge conflicts
- Iteration 3: No comments — PR approved

### Quality: All checks passed
```

---

## Important Rules

- **Push fixes BEFORE resolving conflicts** — conflict resolution triggers re-review
- **Never auto-resolve security comments** without manual verification
- **Always run quality checks** before pushing — never push broken code
- **Use CodeRabbit's exact suggestions** when provided — don't "improve" them
- **Max 3 attempts per comment** — escalate after 3 failures
- **Use `@coderabbitai` mentions** to communicate with CodeRabbit

## Error Handling

### Quality Check Failures
- Apply the fix, re-run checks, iterate (max 3 attempts per comment)
- After 3 failures: post escalation reply and move to next comment

### Push Failures
- Pull latest, resolve any new conflicts, retry push

### Comment Processing Failures
Post escalation reply:
```
@coderabbitai

After 3 attempts, I'm unable to resolve this issue automatically.

**Attempts made:**
1. [attempt 1]
2. [attempt 2]
3. [attempt 3]

**Blocker:** [why it's not working]

Escalating to human review.
```
