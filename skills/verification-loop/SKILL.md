---
name: verification-loop
description: A comprehensive verification system for Claude Code sessions. Run after completing features or before creating PRs.
model: sonnet
allowed-tools: Read, Bash, Grep, Glob
---

# Verification Loop Skill

A comprehensive verification system for Claude Code sessions.

## When to Use

Invoke this skill:
- After completing a feature or significant code change
- Before creating a PR
- When you want to ensure quality gates pass
- After refactoring

## Verification Phases

### Phase 1: Type Check
```bash
# Run mypy
mypy app/ --ignore-missing-imports 2>&1 | head -30
```

Report all type errors. Fix critical ones before continuing.

### Phase 2: Lint Check
```bash
# Run ruff
ruff check . 2>&1 | head -30

# Auto-fix where possible
ruff check --fix . 2>&1 | head -10
```

### Phase 3: Format Check
```bash
# Check formatting
ruff format --check . 2>&1 | head -10

# Auto-format
ruff format .
```

### Phase 4: Test Suite
```bash
# Run tests with coverage
pytest --cov=app --cov-report=term-missing 2>&1 | tail -50

# Check coverage threshold
# Target: 80% minimum
```

Report:
- Total tests: X
- Passed: X
- Failed: X
- Coverage: X%

### Phase 5: Security Scan
```bash
# Run bandit
bandit -r app/ -ll 2>&1 | head -30

# Check for secrets
grep -rn "sk-" --include="*.py" . 2>/dev/null | head -10
grep -rn "api_key\s*=" --include="*.py" . 2>/dev/null | head -10

# Check for print statements
grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok" | head -10
```

### Phase 6: Dependency Audit
```bash
# Check for vulnerabilities
pip-audit 2>&1 | head -20

# Or with safety
safety check 2>&1 | head -20
```

### Phase 7: Diff Review
```bash
# Show what changed
git diff --stat
git diff HEAD~1 --name-only
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Potential edge cases

## Output Format

After running all phases, produce a verification report:

```
VERIFICATION REPORT
==================

Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Format:    [PASS/FAIL]
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Prints:    [PASS/FAIL] (X found)
Deps:      [PASS/FAIL] (X vulnerabilities)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## Quick Mode

For rapid iteration during development:

```bash
# Quick verification (types + lint only)
mypy app/ --ignore-missing-imports && ruff check .
```

## Pre-Commit Mode

For commits:

```bash
# Pre-commit checks
mypy app/ --ignore-missing-imports && \
ruff check . && \
pytest tests/unit -x -q && \
grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok" | wc -l
```

## Pre-PR Mode

Full checks plus security scan:

```bash
# Full verification
make ci
# OR manually:
mypy app/ && \
ruff check . && \
pytest --cov=app --cov-fail-under=80 && \
bandit -r app/ -ll && \
grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok"
```

## Continuous Mode

For long sessions, run verification every 15 minutes or after major changes:

```markdown
Set a mental checkpoint:
- After completing each function
- After finishing a component
- Before moving to next task

Run: /verify
```

## Integration with Hooks

This skill complements PostToolUse hooks but provides deeper verification.
Hooks catch issues immediately; this skill provides comprehensive review.

## Makefile Integration

```makefile
# In Makefile
.PHONY: verify
verify:
	@echo "=== Type Check ==="
	mypy app/ --ignore-missing-imports
	@echo "=== Lint Check ==="
	ruff check .
	@echo "=== Tests ==="
	pytest --cov=app --cov-report=term-missing
	@echo "=== Security ==="
	bandit -r app/ -ll
	@echo "=== Print Statements ==="
	@grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok" || echo "None found"
```

## Pre-PR Checklist

Before creating a PR, verify:

- [ ] `mypy app/` passes
- [ ] `ruff check .` passes
- [ ] `pytest` passes (80%+ coverage)
- [ ] `bandit -r app/` no high severity
- [ ] No `print()` statements
- [ ] No hardcoded secrets
- [ ] Documentation updated if needed
- [ ] Dignified Python rules followed
