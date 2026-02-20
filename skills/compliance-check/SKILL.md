---
name: compliance-check
description: Check code against applicable standards. Used by QA Agent.
model: opus
allowed-tools: Read, Grep, Glob
---

# Compliance Check

Verify code complies with project standards.

## Input

- **files**: Files to check (paths or patterns)
- **standard**: Specific standard to check against (optional, auto-detected if omitted)

## Process

1. **Identify applicable standards**
   - Consult `skills/standards-lookup/SKILL.md`
   - Match file type to standard:
     - `*.py` → `code_style_standards.md`
     - `test_*.py` → `testing_standards.md`
     - `app/api/*.py` → `api_standards.md`

2. **Check code style** (for Python files)
   ```
   Grep: "except:"              # Bare except
   Grep: "except.*:[\s]*pass"   # Swallowed exception
   Grep: "print\("              # Debug prints
   Grep: "def [a-z_]+\([^:)]+\)[^-]"  # Missing type hints
   ```

3. **Check test structure** (for test files)
   ```
   # Verify AAA pattern
   # Check for meaningful assertions
   # Check for edge case coverage
   ```

4. **Check API compliance** (for API files)
   ```
   # Verify response format
   # Check HTTP methods
   # Verify error handling
   ```

5. **Compare against verification checklist**
   - Read checklist from applicable standard
   - Check each item

## Output

```markdown
## Compliance Check: `app/services/user_service.py`

**Standard:** `standards/code_style_standards.md`

### Violations

| Line | Issue | Standard Rule |
|------|-------|---------------|
| 45 | Bare `except:` clause | Never swallow exceptions |
| 78 | Missing return type | Type annotations required |
| 102 | Mutable default `[]` | Rule #10: No mutable defaults |

### Passed
- [x] Import order correct
- [x] Naming conventions followed
- [x] LBYL pattern used
```

## Empty State Handling

**If no applicable standard found:**
```markdown
## Compliance Check: `[file]`

**Standard:** None specifically applicable

### General Checks Applied
- [x] No syntax errors
- [x] No obvious security issues
- [ ] Consider adding to project-standards.yaml if this file type is common
```

**If file doesn't exist:**
```markdown
## Compliance Check: `[file]`

**Status:** ❌ File not found

Cannot check compliance for non-existent file.
```

## Skill Dependencies

```
compliance-check (this skill)
    │
    └── standards-lookup (to find applicable standard)
```

## Usage

**QA Agent:** Check files against standards during review
