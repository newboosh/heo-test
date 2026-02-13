---
name: skill-creator
description: Create new Claude Code skills with proper structure, frontmatter, and conventions. Use when creating a new skill, converting a command to a skill, or setting up skill templates.
argument-hint: [skill-name] [description]
---

# Skill Creator

Create new Claude Code skills following official conventions.

## Usage

```
/skill-creator my-skill "Description of what the skill does"
```

## Skill Creation Process

### Step 1: Determine Skill Type

Ask or infer the skill type:

| Type | Description | Key Frontmatter |
|------|-------------|-----------------|
| **Reference** | Guidelines Claude applies automatically | `user-invocable: true` (default) |
| **Task** | Step-by-step workflow | Consider `disable-model-invocation: true` |
| **Background** | Context Claude should know | `user-invocable: false` |
| **Subagent** | Runs in isolation | `context: fork`, `agent: <type>` |

### Step 2: Choose Frontmatter Options

```yaml
---
name: skill-name                    # Required: lowercase, hyphens, max 64 chars
description: What it does and when  # Recommended: triggers auto-invocation
argument-hint: [arg1] [arg2]        # Optional: shown in autocomplete
disable-model-invocation: true      # Optional: user-only (for side effects)
user-invocable: false               # Optional: Claude-only (background knowledge)
allowed-tools: Read, Grep, Bash(*)  # Optional: restrict tool access
model: claude-sonnet                # Optional: override model
context: fork                       # Optional: run in subagent
agent: Explore                      # Optional: subagent type (Explore, Plan, general-purpose)
---
```

### Step 3: Create Directory Structure

```
.claude/skills/<skill-name>/
├── SKILL.md           # Main instructions (required)
├── template.md        # Template for output (optional)
├── examples/          # Example outputs (optional)
│   └── sample.md
└── scripts/           # Supporting scripts (optional)
    └── helper.sh
```

### Step 4: Write SKILL.md Content

**For Reference Skills:**
```markdown
---
name: api-conventions
description: API design patterns for this codebase. Use when creating API endpoints.
---

When writing API endpoints:

1. Use RESTful naming conventions
2. Return consistent error formats
3. Include request validation
4. Document with docstrings
```

**For Task Skills:**
```markdown
---
name: deploy
description: Deploy application to production
disable-model-invocation: true
argument-hint: [environment]
---

Deploy to $ARGUMENTS:

1. Run test suite
2. Build application
3. Push to deployment target
4. Verify health check
```

**For Subagent Skills:**
```markdown
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---

Research $ARGUMENTS:

1. Find relevant files
2. Analyze code patterns
3. Summarize findings with file:line references
```

### Step 5: Use String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed to skill |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `!`command`` | Dynamic context injection (runs before skill loads) |

### Step 6: Validate the Skill

Checklist:
- [ ] Name is lowercase, alphanumeric, hyphens only (max 64 chars)
- [ ] Description explains WHAT it does and WHEN to use it
- [ ] SKILL.md under 500 lines (reference supporting files if larger)
- [ ] `disable-model-invocation: true` for side-effect workflows
- [ ] `user-invocable: false` for background-only knowledge
- [ ] `context: fork` if skill should run in isolation

## Examples

### Example 1: Code Review Skill

```markdown
---
name: review-code
description: Review code changes for quality and security. Use when reviewing PRs or recent changes.
allowed-tools: Read, Grep, Glob, Bash(git:*)
---

Review the code changes:

1. **Check diff**: `git diff HEAD~1`
2. **Security scan**: Look for hardcoded secrets, injection risks
3. **Quality check**: Follow Dignified Python rules
4. **Test coverage**: Verify tests exist for changes

Output format:
- CRITICAL: [issue]
- WARNING: [issue]
- SUGGESTION: [improvement]
```

### Example 2: Documentation Generator

```markdown
---
name: generate-docs
description: Generate documentation for a module or function
argument-hint: [file-or-function]
context: fork
agent: general-purpose
---

Generate documentation for $ARGUMENTS:

1. Read the source code
2. Identify public API
3. Write docstrings in Google style
4. Create usage examples
5. Output as markdown
```

### Example 3: Background Context Skill

```markdown
---
name: legacy-database
description: Context about legacy database patterns in this codebase
user-invocable: false
---

## Legacy Database Patterns

This codebase uses legacy patterns in `app/legacy/`:

- Direct SQL queries (not ORM)
- Custom connection pooling
- Non-standard naming conventions

When working in these files:
- Maintain existing patterns
- Don't refactor without explicit request
- Add comments for unusual code
```

### Example 4: Dynamic Context Skill

```markdown
---
name: pr-review
description: Review the current pull request
context: fork
agent: general-purpose
allowed-tools: Bash(gh:*)
---

## Current PR Context

- **Diff**: !`gh pr diff 2>/dev/null || echo "No PR found"`
- **Comments**: !`gh pr view --comments 2>/dev/null || echo "No PR found"`
- **Files changed**: !`gh pr diff --name-only 2>/dev/null || echo "No PR found"`

## Review Instructions

1. Summarize the changes
2. Check for issues
3. Suggest improvements
```

## Skill Locations

| Location | Path | Scope |
|----------|------|-------|
| Personal | `~/.claude/skills/<name>/SKILL.md` | All projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where enabled |

## Common Patterns

### Workflow Skill (with side effects)
```yaml
disable-model-invocation: true  # User must invoke
```

### Research Skill (isolated)
```yaml
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
```

### Restricted Skill (limited tools)
```yaml
allowed-tools: Read, Grep  # No write access
```

### Model Override
```yaml
model: claude-opus  # Use Opus for complex tasks
```

## Output

After gathering requirements, create:

1. Directory: `.claude/skills/<skill-name>/`
2. File: `SKILL.md` with frontmatter and instructions
3. Optional: Supporting files (templates, examples, scripts)

Confirm the skill works by suggesting the user test with `/<skill-name>`.
