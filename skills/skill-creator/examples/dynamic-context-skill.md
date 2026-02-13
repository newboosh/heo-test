---
name: git-status-review
description: Review current git status and suggest next actions
context: fork
agent: general-purpose
---

# Git Status Review

## Current State

**Branch**: !`git branch --show-current`

**Status**:
```
!`git status --short`
```

**Recent commits**:
```
!`git log --oneline -5`
```

**Uncommitted changes**:
```
!`git diff --stat`
```

## Analysis

Based on the current git state:

1. **Assess the situation**
   - Are there uncommitted changes?
   - Is the branch up to date?
   - Are there untracked files?

2. **Recommend actions**
   - Stage and commit changes
   - Create a branch if on main
   - Push if commits are local only

3. **Warn about issues**
   - Large uncommitted changes
   - Sensitive files in diff
   - Merge conflicts

## Output

Provide actionable recommendations based on the current state.
