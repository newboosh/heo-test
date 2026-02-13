---
name: continuous-learning
description: Automatically extract reusable patterns from Claude Code sessions and save them as learned skills for future use.
---

# Continuous Learning Skill

Automatically evaluates Claude Code sessions on end to extract reusable patterns that can be saved as learned skills.

## How It Works

This skill runs as a **Stop hook** at the end of each session:

1. **Session Evaluation**: Checks if session has enough messages (default: 10+)
2. **Pattern Detection**: Identifies extractable patterns from the session
3. **Skill Extraction**: Saves useful patterns to `.claude/skills/learned/`

## Pattern Types

| Pattern | Description | Example |
|---------|-------------|---------|
| `error_resolution` | How specific errors were resolved | "Fixed ImportError by adding package to requirements.txt" |
| `user_corrections` | Patterns from user corrections | "User prefers f-strings over .format()" |
| `workarounds` | Solutions to framework quirks | "SQLAlchemy needs explicit flush before commit in this pattern" |
| `debugging_techniques` | Effective debugging approaches | "Used pdb.set_trace() to identify race condition" |
| `project_specific` | Project-specific conventions | "This project uses BlueprintX pattern for routes" |

## Patterns to Ignore

- `simple_typos` - One-character fixes
- `one_time_fixes` - Context-specific, won't recur
- `external_api_issues` - Third-party API problems

## Configuration

Edit `config.json` to customize:

```json
{
  "min_session_length": 10,
  "extraction_threshold": "medium",
  "auto_approve": false,
  "learned_skills_path": ".claude/skills/learned/",
  "patterns_to_detect": [
    "error_resolution",
    "user_corrections",
    "workarounds",
    "debugging_techniques",
    "project_specific"
  ],
  "ignore_patterns": [
    "simple_typos",
    "one_time_fixes",
    "external_api_issues"
  ]
}
```

## Hook Setup

Add to your `.claude/settings.json` or project hooks:

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": ".claude/skills/continuous-learning/evaluate-session.sh"
      }]
    }]
  }
}
```

## Why Stop Hook?

- **Lightweight**: Runs once at session end
- **Non-blocking**: Doesn't add latency to every message
- **Complete context**: Has access to full session transcript

## Learned Skills Storage

```
.claude/
  skills/
    learned/
      error-celery-connection.md    # How to fix Celery connection issues
      pattern-flask-blueprints.md   # Blueprint organization learned
      debug-sqlalchemy-n1.md        # N+1 query debugging technique
```

## Example Learned Skill

```markdown
---
name: celery-connection-fix
learned: 2025-01-23
source: session-abc123
---

# Celery Connection Fix

## Pattern
When Celery tasks fail silently, check Redis connection.

## Solution
```python
# Verify Redis is running
redis-cli ping

# Check Celery config
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Add connection retry
app.conf.broker_connection_retry_on_startup = True
```

## When to Apply
- Celery tasks not executing
- No error messages in logs
- Redis container may have restarted
```

## Integration with /learn Command

Use `/learn` to manually extract patterns mid-session:

```
/learn "How to fix SQLAlchemy session issues"
```

This creates a learned skill from the current session context without waiting for session end.

## Related

- `/learn` command - Manual pattern extraction
- `/checkpoint` command - Save session state
- `strategic-compact` skill - Context management
