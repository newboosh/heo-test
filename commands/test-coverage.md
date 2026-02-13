# Test Coverage

Analyze test coverage and return a prioritized gap list. This is the **gap analysis** skill used by `/tdd` as Step 0.

## Process

1. Run tests with coverage:
   ```bash
   pytest --cov=app --cov-report=term-missing --cov-report=html
   ```

2. Analyze coverage report

3. Identify files below threshold (see Coverage Thresholds)

4. Prioritize by type:
   1. Security-critical code (auth, validation)
   2. Core business logic
   3. API endpoints
   4. Utility functions
   5. Error handlers

5. Return structured gap list:
   ```
   COVERAGE GAP ANALYSIS
   =====================
   Overall: 72% (target: 80%)

   Priority 1 (Security - requires 100%):
   - app/auth/login.py: 85% [lines 42-48, 67-71]
   - app/utils/validators.py: 90% [lines 23-25]

   Priority 2 (Core - requires 90%):
   - app/services/email.py: 78% [lines 101-120]

   Priority 3 (API - requires 80%):
   - app/routes/users.py: 65% [lines 45-60, 88-95]

   Files meeting threshold: 12
   Files needing tests: 4
   ```

## Commands

```bash
# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Generate HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Check specific module
pytest --cov=app.services.email tests/

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=80
```

## Coverage Thresholds

| Code Type | Minimum |
|-----------|---------|
| Security (auth, validation) | 100% |
| Core business logic | 90% |
| API routes | 80% |
| Utilities | 80% |
| Overall project | 80% |

## Usage

**Standalone**: Run `/test-coverage` to see current gaps without writing tests.

**With TDD**: The `/tdd` command calls `/test-coverage` as Step 0 to determine what needs tests, then iterates through the gap list.

## Used By

Called by `/tdd` as Step 0 for gap analysis before starting TDD cycles.
