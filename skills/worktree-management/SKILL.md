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

### Complete Work
Commit, push, and optionally create PR.
```
/tree close
```

### Cleanup
Prune local worktrees after PRs are merged.
```
/tree closedone
```

## Integration

The skill integrates with:
- Git worktrees for isolation
- GitHub for PR review
- Claude Code for AI-assisted development

