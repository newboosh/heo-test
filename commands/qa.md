# QA (Quality Assurance Review)

Explicitly invoke the QA Agent to review completed work.

## Usage

```
/qa                          # Review uncommitted changes
/qa <file or directory>      # Review specific files
/qa --staged                 # Review staged changes only
/qa --branch                 # Review all changes on branch
```

## When to Use

The QA Agent activates **proactively** after code changes. Use `/qa` to:
- Explicitly request a review before commit
- Review specific files
- Re-review after making fixes

## Skills Composed

```
/qa
 │
 ├─► Read .claude/project-standards.yaml
 ├─► diff-review       → Scope changes, identify risk
 ├─► standards-lookup  → Find applicable standards
 ├─► compliance-check  → Verify against standards
 ├─► artifact-audit    → Check tests, docs, migrations
 └─► find-patterns     → Check consistency
         │
         ▼
      QA Report
```

## Output

QA Report containing:
- Status (Approved / Needs Changes / Blocked)
- Issues by severity (Critical / Warning / Suggestion)
- Artifact audit results
- Compliance checklist

## Severity Levels

| Level | Action |
|-------|--------|
| **Critical** | Must fix before merge |
| **Warning** | Should fix |
| **Suggestion** | Nice to have |

Invokes the **qa-agent**.

## Error Handling

| Situation | Behavior |
|-----------|----------|
| No changes found | Reports clean status, suggests `--branch` flag |
| No applicable standard | Uses general checks, recommends project-standards.yaml |
| Missing artifact paths | Suggests adding custom paths to project-standards.yaml |
| Project structure not recognized | Provides manual configuration guidance |

## Configuration

Customize QA behavior via `.claude/project-standards.yaml`:
- Override artifact paths for your project structure
- Set required vs optional docstrings/types
- Configure language-specific defaults

See `.claude/project-standards.yaml.template` for examples.
