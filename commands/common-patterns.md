# Common Patterns

Reusable patterns for commands. Reference these instead of duplicating code.

## GitHub Authentication Setup

Use this pattern in commands that need GitHub API access:

```bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/github-auth.sh" && github_auth_setup
github_auth_status
```

**Used by:** `/push`, `/pr-status`, `/coderabbit`

---

## Quality Checks

Use this pattern to verify code quality before commits or pushes:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
```

**Options:**
- `--fix` - Auto-fix issues where possible
- `--quiet` - Suppress non-error output
- `--changed-only` - Only check files changed vs origin/main
- `--staged` - Only check staged files (for pre-commit)

**Used by:** `/push`, `/ci`, `/build-fix`, `/coderabbit process`, `/verify`

---

## PR Detection

Use this pattern to get the current branch's PR number:

```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
if [ -z "$PR_NUMBER" ]; then
    echo "ERROR: No PR found for current branch"
    exit 1
fi
```

**Used by:** `/pr-status`, `/coderabbit`, `coderabbitloop` agent

---

## Branch Protection Check

Use this pattern to prevent direct pushes to protected branches:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    echo "ERROR: Cannot push directly to $CURRENT_BRANCH"
    echo "Create a feature branch first: git checkout -b feature/<name>"
    exit 1
fi
```

**Used by:** `/push`

---

## Conventional Commit Message

Use this format for commit messages:

```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

<body>

Co-Authored-By: Steve Glen, Claude Code <model-name x.x>
EOF
)"
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Used by:** `/push`, `/coderabbit process`, `/coderabbit conflicts`

---

## Push with Tracking Detection

Use this pattern to push with automatic upstream setup:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
    # Branch exists on remote
    git push origin "$CURRENT_BRANCH"
else
    # First push - set up tracking
    git push -u origin "$CURRENT_BRANCH"
fi
```

**Used by:** `/push`

---

## Error Handling Pattern

For commands with retryable operations:

```markdown
### Error Handling

**On failure:**
1. **First attempt**: Try the operation
2. **Retry trigger**: If fails, [specific recovery action]
3. **Iteration limit**: Max N attempts
4. **After N failures**: Escalate with explanation

**Never [dangerous action]** - stop and report to user
```

**Used by:** `/coderabbit process`, `/build-fix`
