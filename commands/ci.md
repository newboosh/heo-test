# Local CI Validation

Run the full CI validation suite locally before pushing.

## When to Use This vs Other Commands

| Task | Command | Why |
|------|---------|-----|
| Before pushing | `/ci` | Full validation matching remote CI |
| Quick check while coding | `/verify quick` | Fast types + lint only |
| Comprehensive inspection | `/verify` | Full checks + print audit + git status |
| Fix build errors iteratively | `/build-fix` | Targets specific errors one at a time |
| Review uncommitted changes | `/code-review` | Security + quality of changes only |

**Use `/ci`** when you want to match what remote CI will run before pushing.

## Instructions

You are running local CI validation. This ensures code passes all quality gates before pushing to remote.

### 1. Full CI Suite

Run the complete validation suite:

```bash
make ci
```

This runs:
- Linting (Ruff, ESLint)
- Type checking (MyPy)
- Security checks (Bandit, Safety, CSP)
- Unit tests
- Integration tests

### 2. If Full CI Fails

Run individual checks to identify the issue:

#### Quality Checks Only
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
```

#### Linting Only
```bash
ruff check .
```

#### Type Checking Only
```bash
mypy .
```

#### Tests Only
```bash
make test-parallel
```

Or for verbose test output:
```bash
pytest -v
```

### 3. Fix Issues

For each failing check:

1. **Linting errors**: Usually auto-fixable with `ruff check --fix .`
2. **Type errors**: Add type hints or fix type mismatches
3. **Test failures**: Read the test output and fix the failing code
4. **Security issues**: Address the security concern (don't just suppress)

### 4. Re-run Validation

After fixes, re-run the full suite:

```bash
make ci
```

### 5. Common Issues

#### Import Errors
```bash
# Check for circular imports
python3 -c "import app"
```

#### Database Tests
Tests may need a running database:
```bash
docker-compose up -d db
```

#### Missing Dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## Quality Standards

This project follows the **Ten Rules for Dignified Python**:

1. LBYL over EAFP
2. Never swallow exceptions
3. Magic methods must be O(1)
4. Check .exists() before .resolve()
5. Defer import-time computation
6. Verify casts at runtime
7. Literal types for fixed values
8. Declare variables close to use
9. Keyword-only args for 5+ params
10. Avoid default values

## Arguments

- `$ARGUMENTS` - Optional: `quick` for quality checks only, `tests` for tests only.
