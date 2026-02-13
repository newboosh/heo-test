# Delegation Pattern Example

This example shows `/coderabbit` delegating push responsibility to `/push`.

## Before (duplicated logic)

```markdown
# /coderabbit

### Step 6: Push Fixes

` ` `bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/github-auth.sh" && github_auth_setup
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
git add -A
git commit -m "fix: address review comments"
BRANCH=$(git branch --show-current)
if git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
    git push origin "$BRANCH"
else
    git push -u origin "$BRANCH"
fi
gh pr view || gh pr create --title "..." --body "..."
` ` `
```

## After (delegation)

```markdown
# /coderabbit

### Step 6: Push Fixes

Stage and commit:
` ` `bash
git add <fixed files>
git commit -m "fix: address CodeRabbit comments"
` ` `

Delegate push to `/push`:
` ` `
/push
` ` `

The `/push` command handles:
- GitHub auth
- Quality checks (skipped if no uncommitted changes)
- Branch detection (new vs existing)
- PR creation/update
```

## Benefits

1. **Single source of truth**: Push logic lives in one place
2. **Automatic improvements**: When `/push` improves, `/coderabbit` benefits
3. **Clearer intent**: Each command does one thing well
4. **Easier testing**: Test push logic once, not in every command
