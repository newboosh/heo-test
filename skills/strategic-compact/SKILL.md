---
name: strategic-compact
description: Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction.
model: haiku
---

# Strategic Compact Skill

Suggests manual `/compact` at strategic points in your workflow rather than relying on arbitrary auto-compaction.

## Why Strategic Compaction?

Auto-compaction triggers at arbitrary points:
- Often mid-task, losing important context
- No awareness of logical task boundaries
- Can interrupt complex multi-step operations

Strategic compaction at logical boundaries:
- **After exploration, before execution** - Compact research context, keep implementation plan
- **After completing a milestone** - Fresh start for next phase
- **Before major context shifts** - Clear exploration context before different task

## When to Compact

### Good Times to Compact

1. **After planning is complete**
   - You've explored the codebase
   - You have a clear implementation plan
   - Ready to start coding

2. **After debugging session**
   - Bug is fixed
   - Clear error-resolution context
   - Ready for next task

3. **After completing a feature**
   - Tests are passing
   - Code is reviewed
   - Moving to different area

4. **Before context-heavy task**
   - About to explore new area
   - Want fresh context space
   - Previous context no longer relevant

### Bad Times to Compact

1. **Mid-implementation**
   - Still making related changes
   - Need context for consistency

2. **During debugging**
   - Still investigating
   - Need error context

3. **Between related changes**
   - Multi-file refactor in progress
   - Need to remember what was changed

## Usage Pattern

```markdown
# After planning phase
"I've explored the codebase and have a plan. Let me compact before implementation."
/compact

# After debugging
"Bug is fixed and tests pass. Let me compact before the next task."
/compact

# Before major shift
"Done with auth changes. Compacting before working on the API."
/compact
```

## What Gets Preserved

After compaction:
- Summary of what was accomplished
- Key decisions made
- Current state of work
- Important file locations

What's lost:
- Detailed exploration steps
- Intermediate attempts
- Full error messages (summarized)

## Automatic Suggestions

The `suggest-compact.sh` script can run on PreToolUse to automatically suggest compaction:

### Hook Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "tool == \"Edit\" || tool == \"Write\"",
      "hooks": [{
        "type": "command",
        "command": ".claude/skills/strategic-compact/suggest-compact.sh"
      }]
    }]
  }
}
```

### Thresholds

| Tool Calls | Action |
|------------|--------|
| 50 | First suggestion to compact |
| 75, 100, 125... | Periodic reminders every 25 calls |
| 100 | Strong recommendation |
| 150 | Warning: context likely saturated |

### Configuration

Set `COMPACT_THRESHOLD` environment variable to customize:

```bash
export COMPACT_THRESHOLD=40  # Suggest earlier
```

## Best Practices

1. **Document before compacting** - Write key findings to a file if needed
2. **Commit before compacting** - Ensure code changes are saved
3. **Note the current state** - Mention what you're about to work on
4. **Read the summary** - Review what was preserved after compaction

## Related Commands

- `/compact` - Trigger manual compaction
- `/checkpoint` - Save current state to file before compacting
- `/learn` - Extract patterns before they're lost to compaction

## Integration with Workflow

```
1. /plan - Create implementation plan
2. [Exploration and planning]
3. /compact - Clear exploration context
4. [Implementation]
5. /verify - Run verification
6. /compact - Clear implementation context
7. [Next task]
```
