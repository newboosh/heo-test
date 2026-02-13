# Build and Fix

Incrementally fix Python type and lint errors by running `/verify quick` and fixing issues one at a time.

## Overview

This command composes `/verify quick` with an iterative fix loop:

```
/build-fix
    │
    ├─► /verify quick     → Get type + lint errors
    │
    └─► Fix Loop:
        ├─► Parse errors (group by file, sort by severity)
        ├─► For each error:
        │   ├─► Show context (5 lines before/after)
        │   ├─► Explain the issue
        │   ├─► Apply fix
        │   └─► Re-verify
        └─► Repeat until clean or limit reached

```

## Instructions

### 1. Run Initial Verification

**Delegate to `/verify quick`:**
```
/verify quick
```

This runs type checking (mypy) and linting (ruff), producing a report of all errors.

### 2. Parse Error Output

From the verification report:
- Group errors by file
- Sort by severity (type errors before lint warnings)
- Count total errors

If no errors: **STOP** - report success.

### 3. Fix Loop

For each error (one at a time):

1. **Show context** - Read file with 5 lines before/after the error
2. **Explain** - Describe what's wrong and why
3. **Fix** - Apply minimal change to resolve
4. **Re-verify** - Run `/verify quick` again
5. **Check result**:
   - Error resolved → next error
   - New errors introduced → revert, try alternative
   - Same error persists → increment attempt counter

### 4. Stop Conditions

Stop the fix loop if:
- All errors resolved ✓
- Fix introduces new errors (after 2 revert attempts)
- Same error persists after 3 attempts
- User requests pause

### 5. Show Summary

```
BUILD-FIX COMPLETE
==================
Errors fixed:      X
Errors remaining:  Y
New errors:        Z

Files modified:
- file1.py (3 fixes)
- file2.py (1 fix)
```

## Auto-Fix Option

For simple lint issues, ruff can auto-fix:
```bash
ruff check --fix .
```

Use this for straightforward issues (unused imports, formatting), then run `/verify quick` to catch remaining errors that need manual fixes.

## Safety Rules

- Fix one error at a time
- Re-verify after each fix
- Revert if fix introduces new errors
- Never suppress errors without understanding them

Invokes the **build-error-resolver** agent.
