---
name: worktree-management
description: Manage parallel development using git worktrees.
model: haiku
allowed-tools: Read, Bash, Grep, Glob
---

# Worktree Management Skill

Manage parallel development using git worktrees.

## Invocation

This skill is automatically available via the `/tree` command.

## Capabilities

### Stage Features
Stage features for batch worktree creation.
```
/tree stage "Add user authentication"
/tree stage "Implement payment processing"
/tree list
```

### Build Worktrees
Create all staged worktrees with isolated branches.
```
/tree build
```

### Remove Worktrees
Remove a single worktree when done with it.
```
/tree close
```

### Prune All Worktrees
Remove all local worktrees at once.
```
/tree closedone
```

## Integration

The skill integrates with:
- Git worktrees for isolation
- GitHub for PR review
- Claude Code for AI-assisted development

