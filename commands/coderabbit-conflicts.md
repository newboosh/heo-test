# CodeRabbit Resolve Conflicts

Resolve merge conflicts for a PR after CodeRabbit comments have been processed.

## Arguments

- `$ARGUMENTS` - Optional PR number. If not provided, detect from current branch.

## Instructions

**You are resolving merge conflicts for a PR.**

**CRITICAL: Only run this AFTER fixes have been pushed.** Resolving conflicts triggers a full CodeRabbit re-review.

---

### 1. Fetch and Merge

```bash
git fetch origin main
git merge origin/main
```

If no conflicts, report success and exit.

---

### 2. Resolve Each Conflict

For each conflicted file:

1. **Review the conflict markers**
   ```
   <<<<<<< HEAD
   our changes
   =======
   their changes
   >>>>>>> origin/main
   ```

2. **Make intelligent merge decisions**
   - Prefer keeping both changes when possible
   - If unclear, keep the PR's changes
   - Preserve functionality from both sides

3. **Verify the resolution**
   - Ensure code is syntactically valid
   - Check that logic is preserved

---

### 3. Verify Quality

After resolving all conflicts:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh
```

If quality checks fail, fix the issues before proceeding.

---

### 4. Commit and Push Resolution

Stage and commit with conflict resolution message:

```bash
git add <resolved files>

git commit -m "$(cat <<'EOF'
fix(merge): resolve conflicts with main

Resolved conflicts in:
- <file1>
- <file2>

Co-Authored-By: Claude Code <noreply@anthropic.com>
EOF
)"
```

Delegate push to `/push`:
```
/push
```

---

### 5. Report Results

Output a summary:
- Files with conflicts resolved
- Resolution strategy used for each
- Quality check status
- Push status

---

## Error Handling

### Conflict Resolution Failures
If merge conflicts cannot be resolved automatically:
- **Standard conflicts**: Preserve both change sets when possible
- **Document decisions**: Explain conflict resolution in commit message
- **Security/logic conflicts**: Post PR comment explaining the issue and request human review
- **Note**: Commit and push the best resolution attempt, then post status comment if human input needed

### Push Failures
When `/push` is called and fails:
- **Git push rejected**: Pull latest, resolve any new conflicts, retry
- **Quality check failure**: Fix code quality issues and re-call `/push`

---

## Used By

This command is called by `/coderabbit` as Step 3 to resolve conflicts.
