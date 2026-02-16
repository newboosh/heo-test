---
name: diff-review
description: Review changed files and identify what to check. Used by QA Agent.
---

# Diff Review

Identify what changed and scope the review.

## Input

- **scope**: What to diff (default: uncommitted changes)
  - `staged` - Only staged changes
  - `head` - Changes since last commit
  - `branch` - Changes on current branch vs main
  - `<commit>` - Changes since specific commit

## Flag Handling (for /qa command)

```
/qa                    → scope = "uncommitted" (default)
/qa <path>             → scope = "uncommitted", filter to <path>
/qa --staged           → scope = "staged"
/qa --branch           → scope = "branch"
/qa --branch <base>    → scope = "branch", base = <base>
```

**Parsing logic:**
1. Check for `--staged` flag → use staged scope
2. Check for `--branch` flag → use branch scope, detect base branch
3. Check for path argument → filter results to path
4. Default → uncommitted changes

**Base branch detection:**
```bash
# Try common base branch names
git rev-parse --verify main 2>/dev/null && echo "main"
git rev-parse --verify master 2>/dev/null && echo "master"
git rev-parse --verify develop 2>/dev/null && echo "develop"
```

## Process

1. **Get changed files**
   ```bash
   git diff --name-only           # Uncommitted
   git diff --name-only --staged  # Staged only
   git diff --name-only HEAD~1    # Since last commit
   git diff --name-only main...   # Branch changes
   ```

2. **Categorize changes**
   ```markdown
   ### By Type
   - **Added:** New files
   - **Modified:** Changed files
   - **Deleted:** Removed files

   ### By Area
   - **Models:** app/models/*.py
   - **Services:** app/services/*.py
   - **API:** app/api/*.py
   - **Tests:** tests/**/*.py
   ```

3. **Identify review focus**
   - Map changed files to applicable standards
   - Flag high-risk changes (auth, payments, data)
   - Note files that should have changed but didn't

4. **Get change statistics**
   ```bash
   git diff --stat  # Lines added/removed
   ```

## Output

```markdown
## Diff Review

### Scope
Changes since: `HEAD~1`
Total files: 4

### Changed Files

| File | Type | Lines | Risk | Standards |
|------|------|-------|------|-----------|
| `app/services/auth_service.py` | Modified | +45/-12 | High | code_style, testing |
| `app/api/auth.py` | Modified | +20/-5 | High | api_standards |
| `tests/unit/test_auth.py` | Added | +80 | Low | testing_standards |
| `README.md` | Modified | +5/-0 | Low | documentation |

### Review Focus
1. **High-risk:** Auth changes require careful security review
2. **Check:** New endpoint needs integration tests
3. **Verify:** Token handling follows RFC 6750

### Potentially Missing
- No migration found (check if models changed)
- CHANGELOG not updated
```

## Empty State Handling

**If no changes found:**
```markdown
## Diff Review

### Scope
Changes since: `HEAD`

### Status
✅ **No changes detected**

No files have been modified. Nothing to review.

**Possible reasons:**
- All changes already committed
- Working directory is clean
- Wrong scope specified (try `--branch` for branch comparison)
```

## Usage

**QA Agent:** Scope review before detailed checks

## Dependencies

- Requires git repository
- Uses `standards-lookup` to map files to standards
