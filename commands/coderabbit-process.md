# CodeRabbit Process Comments

Fetch, process, and fix CodeRabbit review comments for a PR.

## Arguments

- `$ARGUMENTS` - Optional flags and PR number:
  - `<PR_NUMBER>` - PR to process (default: detect from current branch)
  - `--no-resolve` - Don't auto-resolve comments (let CodeRabbit verify)
  - `--no-push` - Don't commit/push changes (for dry-run inspection)
  - `--iteration <N>` - Current iteration number (for commit messages)

## Instructions

**You are processing CodeRabbit comments and applying fixes.**

### 1. Fetch All Unresolved Comments

Fetch both inline and general comments:

```bash
python3 scripts/coderabbit/loop/fetch_comments.py --pr $PR_NUMBER --json
```

This returns structured data:

```json
{
  "pr_number": 123,
  "comments": [
    {
      "thread_id": "abc123",
      "file": "app/auth/login.py",
      "line": 42,
      "body": "Violation of Dignified Rule #1...",
      "severity": "major",
      "rule_number": 1,
      "suggested_fix": { "type": "diff", "new_code": "...", "is_committable": true }
    }
  ],
  "general_comments": [
    {
      "comment_id": "IC_xyz",
      "body": "Consider updating app/utils/helpers.py...",
      "file_references": [{"file_path": "app/utils/helpers.py", "line": 55}],
      "is_actionable": true
    }
  ]
}
```

Also fetch outside-diff comments:
```bash
python3 scripts/coderabbit/loop/fetch_outside_diff_comments.py --pr $PR_NUMBER
```

---

### 2. Process Inline Comments

For each inline comment (from `comments` array):

#### 2.1 Read the File
Use the Read tool to examine the file at the specified location.

#### 2.2 Check for CodeRabbit's Suggested Fix

**CRITICAL: If CodeRabbit provides a committable solution, USE IT EXACTLY.**

CodeRabbit provides fixes in these formats:

1. **Diff blocks** (```diff):
   ```diff
   - old_code
   + new_code
   ```

2. **Suggestion blocks** (```suggestion):
   ```suggestion
   replacement_code
   ```

**When `suggested_fix` exists:**
- Apply the suggested fix EXACTLY as provided
- Do NOT modify or "improve" the suggestion
- Do NOT add extra changes beyond what CodeRabbit suggested

#### 2.3 If NO Suggested Fix Exists

- Parse the Dignified Rule number if present
- Understand what change is requested
- Create a minimal fix that addresses the specific issue

#### 2.4 Apply the Fix

Use the Edit tool. Follow these principles:

**Priority order:**
1. Use CodeRabbit's exact suggestion (highest priority)
2. Apply minimal fix if no suggestion
3. Preserve existing style and formatting

#### 2.5 Verify Locally

Run quality checks (see common-patterns.md):
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh
```

If quality fails, iterate on the fix (max 3 attempts per comment).

#### 2.6 Post Reply

```bash
python3 scripts/coderabbit/loop/post_reply.py --pr $PR_NUMBER --thread <THREAD_ID> --body "<REPLY>"
```

Reply template:
```markdown
@coderabbitai

**Fix applied** at `file.py:line`

[Description of change]

**Verification:** Quality checks passed

Please verify and resolve this thread.
```

---

### 3. Process General Comments

For each general comment (from `general_comments` array) with `file_references`:

1. Read the referenced file(s)
2. Apply the suggested fix (steps 2.2-2.5)
3. Post reply to PR:
```bash
gh pr comment $PR_NUMBER --body "<REPLY>"
```

---

### 4. Auto-Resolve Comments (standalone mode only)

**Skip if `--no-resolve` flag is set.**

After all comments are processed and fixes applied:
```bash
python3 scripts/coderabbit/smart_resolver.py --pr $PR_NUMBER
```

This resolves non-security comments. Security comments require manual verification.

---

### 5. Commit and Push Fixes

**Skip if `--no-push` flag is set or no comments were processed.**

#### 5.1 Stage and Commit

```bash
git add <files that were changed>

git commit -m "$(cat <<'EOF'
fix: address CodeRabbit review comments

- <summary of fix 1>
- <summary of fix 2>

Iteration: <N>/8
PR: #$PR_NUMBER

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

#### 5.2 Push via /push

Delegate push to `/push`:

```
/push
```

**Fixes must be pushed BEFORE resolving conflicts** - this allows CodeRabbit to verify the fixes.

---

### 6. Report Results

Output a summary:
- Number of comments processed
- Files modified
- Quality check status
- Push status

---

## Error Handling

### Quality Check Failures
- **First attempt**: Apply the suggested fix (or create a custom fix)
- **Retry trigger**: If checks fail, iterate on the fix locally and re-run
- **Iteration limit**: Max 3 total attempts per comment
- **After 3 failures**: Escalate with explanation of blocker
- **Never push broken code** - stop and report to user

### Comment Processing Failures
If a comment cannot be fixed after 3 attempts:
- Post escalation reply with specific attempts made and blocker details
- Do not re-attempt in next iteration

---

## Communication Templates

### Fix Applied (with suggestion)
```markdown
@coderabbitai

**Applied your suggested fix** at `file.py:line`

Your suggested change has been applied exactly as provided.

**Verification:** Quality checks passed

Please verify and resolve this thread.
```

### Fix Applied (custom)
```markdown
@coderabbitai

**Fix applied** for [brief description]

**Changes:**
- [specific change with file:line reference]

**Verification:** Quality checks passed
**Rule reference:** Dignified Rule #[N] (if applicable)

Please verify this addresses your concern.
```

### Escalation (after 3 failed attempts)
```markdown
@coderabbitai

After 3 attempts, I'm unable to resolve this issue automatically.

**Attempts made:**
1. [attempt 1]
2. [attempt 2]
3. [attempt 3]

**Blocker:** [why it's not working]

Escalating to human review.
```

## Used By

This command is called by `/coderabbit` as Step 2 to process comments.
