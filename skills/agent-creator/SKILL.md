---
name: agent-creator
description: Create and update Claude Code subagents with proper structure, frontmatter, and conventions. Use when creating a new agent, updating an existing agent, or setting up specialized task handlers.
argument-hint: [agent-name] [description]
---

# Agent Creator

Create and update Claude Code subagents following official conventions.

## Usage

```
/agent-creator my-agent "Description of what the agent does"
```

## What Are Subagents?

Subagents are specialized AI assistants that:
- Handle specific tasks in isolated context windows
- Have custom system prompts and tool access
- Run with independent permissions
- Can be invoked automatically or explicitly

## Agent Creation Process

### Step 1: Determine Agent Purpose

Ask or infer the agent's role:

| Type | Purpose | Example |
|------|---------|---------|
| **Reviewer** | Analyze without modifying | code-reviewer, security-auditor |
| **Worker** | Perform specific tasks | debugger, refactorer, migrator |
| **Researcher** | Gather information | explorer, doc-finder |
| **Specialist** | Domain expertise | data-scientist, db-admin |

### Step 2: Choose Location

| Location | Scope | Path |
|----------|-------|------|
| Project | This repo only | `.claude/agents/<name>.md` |
| Personal | All your projects | `~/.claude/agents/<name>.md` |
| Plugin | Where plugin enabled | `<plugin>/agents/<name>.md` |

### Step 3: Configure Frontmatter

```yaml
---
name: agent-name                    # Required: lowercase, hyphens only
description: What and when          # Required: triggers auto-delegation
tools: Read, Grep, Glob, Bash       # Optional: allowed tools (inherits all if omitted)
disallowedTools: Write, Edit        # Optional: tools to block
model: sonnet                       # Optional: sonnet, opus, haiku, inherit
permissionMode: default             # Optional: default, acceptEdits, dontAsk, bypassPermissions, plan
skills:                             # Optional: skills to preload
  - api-conventions
hooks:                              # Optional: lifecycle hooks
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
---
```

### Step 4: Write System Prompt

The markdown body becomes the agent's system prompt:

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Grep, Glob, Bash
---

You are a senior code reviewer ensuring high standards.

When invoked:
1. Run git diff to see recent changes
2. Focus on modified files
3. Begin review immediately

## Review Checklist

- [ ] Code is clear and readable
- [ ] Functions well-named
- [ ] No duplicated code
- [ ] Proper error handling
- [ ] No exposed secrets
- [ ] Input validation present
- [ ] Good test coverage

## Output Format

Organize feedback by priority:
- **Critical** (must fix)
- **Warning** (should fix)
- **Suggestion** (consider)

Include specific examples of how to fix issues.
```

## Frontmatter Reference

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier (lowercase letters & hyphens) |
| `description` | What the agent does and when Claude should use it |

### Tool Access

| Field | Description |
|-------|-------------|
| `tools` | Comma-separated list of allowed tools |
| `disallowedTools` | Tools to explicitly block |

**Available Tools:**
- File: `Read`, `Write`, `Edit`, `Glob`, `Grep`
- System: `Bash`, `Task`, `WebFetch`, `WebSearch`
- Special: `NotebookEdit`, `AskUserQuestion`

**Read-Only Pattern:**
```yaml
tools: Read, Glob, Grep
```

**Full Access with Restrictions:**
```yaml
tools: Read, Write, Edit, Bash, Grep, Glob
disallowedTools: Task
```

### Model Selection

| Value | When to Use |
|-------|-------------|
| `inherit` | Use parent's model (default) |
| `haiku` | Fast, simple tasks |
| `sonnet` | Balanced performance |
| `opus` | Complex reasoning |

### Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Standard permission prompts |
| `acceptEdits` | Auto-accept file edits |
| `dontAsk` | Auto-deny prompts (allowed tools work) |
| `bypassPermissions` | Skip all checks (careful!) |
| `plan` | Read-only exploration |

### Skill Preloading

```yaml
skills:
  - api-conventions
  - error-handling
```

Skills are injected into the agent's context at startup.

### Lifecycle Hooks

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-command.sh"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "./scripts/run-linter.sh"
```

## Built-in Agents

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| `Explore` | Haiku | Read-only | Fast codebase search |
| `Plan` | Inherits | Read-only | Research for planning |
| `general-purpose` | Inherits | All | Complex multi-step tasks |
| `Bash` | Inherits | Bash | Terminal commands |

## Agent Patterns

### Read-Only Reviewer

```yaml
---
name: code-reviewer
description: Reviews code for quality, security, and maintainability
tools: Read, Grep, Glob, Bash
model: sonnet
---
```

### Worker with Edit Access

```yaml
---
name: refactorer
description: Refactors code to improve quality
tools: Read, Write, Edit, Grep, Glob, Bash
permissionMode: acceptEdits
---
```

### Database Query Validator

```yaml
---
name: db-reader
description: Execute read-only database queries
tools: Bash
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate-readonly-query.sh"
---
```

### Specialist with Skills

```yaml
---
name: api-developer
description: Develops API endpoints following conventions
tools: Read, Write, Edit, Bash, Grep, Glob
skills:
  - api-conventions
  - security-review
---
```

## Validation Checklist

Before saving the agent:

- [ ] `name` is lowercase with hyphens only
- [ ] `description` explains WHAT it does and WHEN to use it
- [ ] Tools are appropriately restricted
- [ ] System prompt is clear and actionable
- [ ] Output format is specified
- [ ] Workflow steps are defined

## When Agents Are Used

### Automatic Delegation

Claude delegates when:
- Task matches agent's `description`
- Task requires specific tool restrictions
- Task is self-contained
- Output should be isolated

### Explicit Invocation

```
Use the code-reviewer agent to review my changes
Have the debugger fix this error
```

### Resuming Agents

```
Continue that code review and analyze the auth logic
```

Resumed agents retain full conversation history.

## Project-Level Hooks

In `.claude/settings.json`:

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/setup-db.sh" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "db-agent",
        "hooks": [
          { "type": "command", "command": "./scripts/cleanup-db.sh" }
        ]
      }
    ]
  }
}
```

## Disabling Agents

In `settings.json`:

```json
{
  "permissions": {
    "deny": ["Task(Explore)", "Task(my-custom-agent)"]
  }
}
```

## Output

After gathering requirements, create:

1. File: `.claude/agents/<agent-name>.md`
2. Frontmatter with proper configuration
3. System prompt with:
   - Role description
   - Workflow steps
   - Checklist/criteria
   - Output format
4. Optional: Supporting scripts for hooks

Test by asking Claude to use the agent or triggering via description match.

## Best Practices

1. **Focus on one task** - Each agent should excel at one thing
2. **Write detailed descriptions** - Helps Claude decide when to delegate
3. **Limit tool access** - Grant only necessary permissions
4. **Specify output format** - Clear expectations for results
5. **Include workflow steps** - Guide the agent's process
6. **Use meaningful names** - `code-reviewer` not `agent1`
7. **Check into version control** - Share with team
