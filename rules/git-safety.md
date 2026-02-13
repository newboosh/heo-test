# Git Safety Rules

These rules apply to ALL repositories and ALL git operations.

## BLOCKED OPERATIONS - NO EXCEPTIONS

The following operations are **always blocked** by the frosty plugin hooks. There are **no valid cases** for these operations. They cannot be bypassed.

### 1. `--no-verify` - ALWAYS BLOCKED
```
git commit --no-verify     # BLOCKED
git push --no-verify       # BLOCKED
git merge --no-verify      # BLOCKED
```
- **No exceptions. No valid cases. Always blocked.**
- Pre-commit hooks exist to enforce code quality and security
- If hooks fail, fix the issue - bypassing is never acceptable

### 2. Direct Push to Main/Master - ALWAYS BLOCKED
```
git push origin main       # BLOCKED
git push origin master     # BLOCKED
git push upstream main     # BLOCKED
```
- **No exceptions. No valid cases. Always blocked.**
- All changes to main/master must go through pull requests
- This includes CI/CD systems - they must use PRs too

### 3. Force Push to Main/Master - ALWAYS BLOCKED
```
git push --force origin main      # BLOCKED
git push -f origin master         # BLOCKED
git push --force-with-lease main  # BLOCKED
```
- **No exceptions. No valid cases. Always blocked.**
- Force push destroys history and can cause data loss
- Force push to feature branches is allowed

### 4. Destructive Operations - ALWAYS BLOCKED
```
git reset --hard           # BLOCKED
git clean -f               # BLOCKED
git checkout -- .          # BLOCKED (discards all changes)
```
- **No exceptions. No valid cases. Always blocked.**
- These operations destroy uncommitted work
- Use `git stash` instead if you need to save changes

### 5. Hook/Signing Bypass via Config - ALWAYS BLOCKED
```
git -c core.hooksPath=/dev/null commit    # BLOCKED
git -c commit.gpgsign=false commit        # BLOCKED
```
- **No exceptions. No valid cases. Always blocked.**
- Config overrides that bypass security are not allowed

## Commit Messages

Follow the **Conventional Commits** specification.

See: `.claude/standards/conventional_commits_full_spec.md`
or `https://www.conventionalcommits.org/en/v1.0.0/#specification`

Quick reference:
```
<type>[optional scope]: <description>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
```

Examples:
```bash
feat(auth): add two-factor authentication
fix(api): handle null response gracefully
refactor(models): simplify User validation
```

## Safe Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit with conventional format
git add <specific-files>
git commit -m "feat: add user authentication"

# Push to feature branch
git push -u origin feature/my-feature

# Create PR for review
gh pr create
```

## Branch Naming Conventions

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation changes
- `task/` - Task-based branches (worktree system)
- `dev/` - Development branches

## Enforcement

These rules are enforced by:
1. Pre-commit hooks
2. Branch protection rules
3. CI/CD pipelines
4. CodeRabbit reviews

Violations should be flagged and corrected immediately.
