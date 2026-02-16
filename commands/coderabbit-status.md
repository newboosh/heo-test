# CodeRabbit Status Check

Check the status of a PR for CodeRabbit review processing.

## Arguments

- `$ARGUMENTS` - Optional PR number. If not provided, detect from current branch.

## Instructions

**You are checking PR status to determine what action is needed.**

### 1. Identify the PR

```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
if [ -z "$PR_NUMBER" ]; then
    echo "ERROR: No PR found for current branch"
    exit 1
fi
echo "Checking PR #$PR_NUMBER"
```

### 2. Check PR Status

```bash
python3 scripts/coderabbit/check_pr_status.py --pr $PR_NUMBER --json
```

### 3. Categorize and Report

Parse the output and report one of these states:

| State | Meaning | Next Action |
|-------|---------|-------------|
| **REVIEWING** | CodeRabbit review in progress | Wait and retry later |
| **COMMENTS** | Has unresolved comments | Run `/coderabbit process` |
| **CONFLICTS_BLOCKED** | Has conflicts AND comments | Run `/coderabbit process`, then `/coderabbit conflicts` |
| **CONFLICTS_ONLY** | Has conflicts, no comments | Run `/coderabbit conflicts` |
| **CLEAN** | No comments, no conflicts | PR is ready |

### 4. Output Format

```
PR #123 Status: COMMENTS

Unresolved comments: 3
Merge conflicts: No
CodeRabbit reviewing: No

Recommended action: /coderabbit process
```

## Used By

This command is called by `/coderabbit` as Step 1 to determine workflow.
