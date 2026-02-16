# Verification Command

Run comprehensive verification on current codebase state.

## When to Use This vs Other Commands

| Task | Command | Why |
|------|---------|-----|
| Quick check while coding | `/verify quick` | Fast types + lint only |
| Comprehensive inspection | `/verify` | Full checks + print audit + git status |
| Before pushing | `/ci` | Matches remote CI pipeline |
| Fix build errors iteratively | `/build-fix` | Targets specific errors one at a time |
| Review uncommitted changes | `/code-review` | Security + quality of changes only |

**Use `/verify`** for comprehensive codebase inspection with print statement audit and git status.

## Instructions

Execute verification in this exact order:

1. **Type Check**
   - Run mypy
   - Report all errors with file:line

2. **Lint Check**
   - Run ruff
   - Report warnings and errors

3. **Test Suite**
   - Run pytest
   - Report pass/fail count
   - Report coverage percentage

4. **Print Statement Audit**
   - Search for `print()` in source files
   - Report locations

5. **Security Check**
   - Run bandit
   - Report vulnerabilities

6. **Git Status**
   - Show uncommitted changes
   - Show files modified since last commit

## Output

Produce a concise verification report:

```
VERIFICATION: [PASS/FAIL]

Types:    [OK/X errors]
Lint:     [OK/X issues]
Tests:    [X/Y passed, Z% coverage]
Security: [OK/X issues]
Prints:   [OK/X found]

Ready for PR: [YES/NO]
```

If any critical issues, list them with fix suggestions.

## Arguments

$ARGUMENTS can be:
- `quick` - Only types + lint
- `full` - All checks (default)
- `pre-commit` - Checks relevant for commits
- `pre-pr` - Full checks plus security scan

## Commands

```bash
# Quick verification
mypy app/ --ignore-missing-imports && ruff check .

# Full verification
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh" && make test-parallel 2>/dev/null || pytest -v 2>/dev/null || echo "Tests skipped"

# Security scan
bandit -r app/ -ll

# Check for prints
grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok"
```
