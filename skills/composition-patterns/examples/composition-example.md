# Composition Pattern Example

This example shows `/qa` orchestrating multiple skills into a unified review.

## Structure

```
/qa
 │
 ├─► diff-review       → What changed? Risk level?
 │       │
 │       ▼ (if high-risk)
 ├─► process-map       → What processes affected?
 │
 ├─► standards-lookup  → Which rules apply?
 │
 ├─► compliance-check  → Does code follow rules?
 │
 ├─► artifact-audit    → Tests? Docs? Migrations?
 │
 └─► find-patterns     → Consistent with codebase?
         │
         ▼
    Aggregate into QA Report
```

## Implementation

```markdown
## Composed Skills

| Skill | Purpose | Output |
|-------|---------|--------|
| `diff-review` | Scope changes, assess risk | Changed files, risk level |
| `process-map` | Map affected processes | Process dependencies |
| `standards-lookup` | Find applicable standards | List of rules |
| `compliance-check` | Verify against standards | Violations list |
| `artifact-audit` | Check required artifacts | Missing items |
| `find-patterns` | Check consistency | Inconsistencies |

## Workflow

### Step 1: Scope
Run `diff-review` to understand what changed.

### Step 2: Risk Assessment
If high-risk changes, run `process-map` to identify blast radius.

### Step 3: Standards
Run `standards-lookup` to find applicable rules.

### Step 4: Compliance
Run `compliance-check` against each applicable standard.

### Step 5: Artifacts
Run `artifact-audit` to verify tests, docs, migrations exist.

### Step 6: Patterns
Run `find-patterns` to check consistency with existing code.

### Step 7: Aggregate
Combine all findings into unified report:

` ` `markdown
# QA Review

**Status:** ✅ APPROVED / ⚠️ NEEDS CHANGES / ❌ BLOCKED

## Issues

### Critical
- [From compliance-check]

### Warnings
- [From find-patterns]

## Artifacts
| Artifact | Status |
|----------|--------|
| Unit tests | ✅ |
| Migration | ❌ Missing |

## Checklist
- [x] Standards compliance
- [ ] Tests present
` ` `
```

## Aggregation Strategy

**Priority-based**: Most severe finding determines overall status.

```
BLOCKED   if any Critical issues
NEEDS     if any Warnings
APPROVED  if only Suggestions or clean
```

## Benefits

1. **Comprehensive**: Multiple perspectives on same changes
2. **Modular**: Each skill is independently useful
3. **Extensible**: Add new checks without changing orchestrator
4. **Consistent**: Same skills, same standards across all reviews
