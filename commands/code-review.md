# Code Review

Comprehensive security and quality review of uncommitted changes.

## Process

1. Get changed files: `git diff --name-only HEAD`

2. For each changed file, check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities (raw SQL with f-strings)
- XSS vulnerabilities (unescaped template output)
- Missing input validation
- Insecure dependencies
- Path traversal risks

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- `print()` statements in production code
- TODO/FIXME comments without tickets
- Missing docstrings for public APIs

**Dignified Python Rules:**
- LBYL over EAFP violations
- Bare `except: pass` (swallowed exceptions)
- Magic methods not O(1)
- Missing `.exists()` before `.resolve()`
- Mutable default arguments
- Missing type hints

**Best Practices (MEDIUM):**
- Missing tests for new code
- Inconsistent naming
- Import * usage
- Circular imports

3. Generate report with:
   - Severity: CRITICAL, HIGH, MEDIUM, LOW
   - File location and line numbers
   - Issue description
   - Suggested fix
   - Dignified Python rule number if applicable

4. Block commit if CRITICAL or HIGH issues found

## Commands

```bash
# Check for print statements
grep -rn "print(" app/ --include="*.py" | grep -v "# debug ok"

# Check for hardcoded secrets
grep -rE "(api[_-]?key|password|secret|token)\s*=" --include="*.py" app/

# Security scan
bandit -r app/ -ll

# Lint check
ruff check .
```

Invokes the **code-reviewer** agent.

Never approve code with security vulnerabilities!
