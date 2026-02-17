# Smart Push Workflow

Push changes safely with automatic branch protection and PR creation.

Automatically detects whether the branch exists on remote and handles both first-time pushes (with tracking) and subsequent pushes.

## Environment Setup

This command requires GitHub authentication. Configure the origin repo in your project root `.env.local`:

```bash
REPO_ORIGIN_URL=https://github.com/username/repo.git
REPO_ORIGIN_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
```

**For worktrees:** The config is loaded automatically from the parent directory. The `github-auth.sh` script will traverse up to 10 directories to find `.env.local`.

**Verify config is loaded:**
```bash
echo $REPO_ORIGIN_URL  # Should show your repo URL
echo "${REPO_ORIGIN_PAT:0:6}..."  # Show only first few chars for security
```

## Instructions

Follow this workflow to push code changes safely.

```text
/push [commit message]
    │
    Step 1: Auth + branch protection
    │
    Step 2: Are there uncommitted changes?
    │       ├─► YES → Quality checks → Stage → Commit
    │       └─► NO  → Skip to Step 3
    │
    Step 3: Are there unpushed commits?
    │       ├─► YES → Push (with -u detection)
    │       └─► NO  → Report "Nothing to push"
    │
    Step 4: Does PR exist?
    │       ├─► YES → Report PR status
    │       └─► NO  → Create PR
```

### 1. Setup and Validation

**Load and sync GitHub auth:**
```bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/github-auth.sh" && github_auth_setup
github_auth_status
```

**Verify config is available:**
```bash
if [ -z "$REPO_ORIGIN_PAT" ] && [ -z "$GITHUB_PAT" ]; then
    echo "Error: REPO_ORIGIN_PAT not found. Check .env.local in project root"
    exit 1
fi
```

**Get current branch and check protection:**
```bash
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    echo "ERROR: Cannot push directly to $CURRENT_BRANCH"
    echo "Create a feature branch first: git checkout -b feature/<name>"
    exit 1
fi
```

### 2. Stage and Commit (if uncommitted changes)

**Check for uncommitted changes:**
```bash
git status --porcelain
```

**If there are uncommitted changes:**

Run quality checks:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
```

If quality checks fail, fix the issues before proceeding.

Stage and commit:
```bash
git add -A
git status  # Review what's staged
```

Create a descriptive commit message:
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Keep the first line under 72 characters
- Reference issue numbers if applicable

```bash
git commit -m "<type>: <description>"
```

**If no uncommitted changes:** Skip to Step 3.

### 3. Push to Remote (if unpushed commits)

**Check for unpushed commits:**
```bash
git log origin/$CURRENT_BRANCH..$CURRENT_BRANCH --oneline 2>/dev/null || git log --oneline -1
```

**If there are unpushed commits:**

Detect if branch exists on remote and push appropriately:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
    # Branch exists on remote - regular push
    echo "Pushing to existing remote branch..."
    git push origin "$CURRENT_BRANCH"
else
    # First push - set up tracking
    echo "First push - setting up upstream tracking..."
    git push -u origin "$CURRENT_BRANCH"
fi
```

**If no unpushed commits:** Report "Nothing to push" and skip to Step 4.

### 4. Create or Update PR

**Check if a PR already exists:**
```bash
gh pr view --json number,url 2>/dev/null || echo "No PR exists yet"
```

**If PR exists:** Report PR status and skip PR creation.

**If no PR exists, create one:**
```bash
gh pr create --title "<title>" --body "## Summary
<description>

## Changes
- <change 1>
- <change 2>

## Test Plan
- [ ] Quality checks pass
- [ ] Tests pass
"
```

### 5. Post-Push Status

After pushing, check PR status:

```bash
gh pr view --json state,mergeable,reviewDecision
```

**Important:** After this point, the push workflow is complete. No additional agents (like `tdd-guide`) are automatically invoked. The focus shifts to PR review and code approval, not test strategy.

The responsibility passes to:
- CodeRabbit for automated review (if enabled on the repository)
- Human reviewers for code approval
- CI/CD pipeline for automated testing (if configured)

## Safety Rules

- **Never push to main directly**
- **Always run quality checks first**
- **Don't skip pre-commit hooks** (`--no-verify` is forbidden)
- **Don't force push** unless explicitly requested and understood

### Forbidden Commands

```bash
# NEVER push directly to main
git push origin main
git push -u origin main

# NEVER skip hooks
git commit --no-verify
git push --no-verify
```

### User Responsibilities

The following are the USER's responsibility, not Claude's:
- Merging PRs to main
- Approving changes to main branch
- Deciding when to deploy

## Error Handling

### Quality Check Failures
If quality checks fail in Step 2:
- The push is halted and the agent stops
- You must manually fix the issues and re-run `/push`
- No automatic retry mechanism

### Push Failures
If `git push` fails in Step 3:
- Network errors: Retry after checking connection
- Rejected pushes (fast-forward rejected, e.g., remote has new commits): Pull the latest and merge/rebase locally, then retry
- Hook failures: Fix the issue locally and re-run `/push`

### PR Creation Failures
If `gh pr create` fails in Step 4:
- Check GitHub token validity: `gh auth status`
- Verify branch is pushed and tracked
- Manually create PR if automatic creation fails

## Arguments

- `$ARGUMENTS` - Optional commit message. If not provided, prompt for one.



## Pre-PR Checklist

Before creating a PR, verify:

- [ ] `mypy hooks/ scripts/ .dev/` passes
- [ ] `ruff check .` passes
- [ ] `pytest` passes (80%+ coverage)
- [ ] `bandit -r hooks/ scripts/ .dev/` no high severity
- [ ] No `print()` statements
- [ ] No hardcoded secrets
- [ ] Documentation updated if needed
