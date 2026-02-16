---
name: AGENT_NAME
description: AGENT_DESCRIPTION. Use when TRIGGER_CONDITION.
tools: Read, Grep, Glob, Bash
# disallowedTools: Write, Edit
# model: sonnet
# permissionMode: default
# skills:
#   - skill-name
# hooks:
#   PreToolUse:
#     - matcher: "Bash"
#       hooks:
#         - type: command
#           command: "./scripts/validate.sh"
---

# AGENT_NAME

You are a ROLE_DESCRIPTION.

## When Invoked

1. First step
2. Second step
3. Third step

## Checklist

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Output Format

Provide output in this format:

```
## Summary
Brief summary of findings/actions

## Details
Detailed information organized by category

## Recommendations
Actionable next steps
```
