# PR Status Check

Check the status of a Pull Request including merge conflicts, CI status, and CodeRabbit threads.

## Instructions

You are checking the status of a Pull Request.

### Prerequisites: Setup GitHub Auth

Ensure `gh` CLI is authenticated with the correct token:

```bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/github-auth.sh" && github_auth_setup
```

### 1. Get PR Number

If not provided, get from current branch:

```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
if [ -z "$PR_NUMBER" ]; then
    echo "No PR found for current branch. Create one with: gh pr create"
    exit 1
fi
echo "Checking PR #$PR_NUMBER"
```

### 2. Check PR Status

Run the comprehensive status check:

```bash
python3 scripts/coderabbit/check_pr_status.py --pr <PR_NUMBER>
```

This shows:
- PR title and state
- Base and head branches
- Mergeable status
- Merge conflicts (if any)
- Unresolved CodeRabbit threads

### 3. Check CI Status

View GitHub Actions workflow status:

```bash
gh pr checks <PR_NUMBER>
```

### 4. View PR Details

Get full PR information:

```bash
gh pr view <PR_NUMBER>
```

### 5. View CodeRabbit Summary

Check the CodeRabbit review summary:

```bash
gh pr view <PR_NUMBER> --comments | head -100
```

## Common Actions Based on Status

### If Merge Conflicts
```bash
git fetch origin main
git merge origin/main
# Resolve conflicts
git add -A
git commit -m "fix: resolve merge conflicts"
git push
```

### If CI Failing
```bash
# Run local CI to debug
make ci
```

### If Unresolved Threads
```bash
# Use coderabbit command
/coderabbit <PR_NUMBER>
```

### If Ready to Merge
```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

## Arguments

- `$ARGUMENTS` - Optional PR number. If not provided, detect from current branch.
