---
description: Enforce test-driven development workflow. Write tests FIRST, then implement minimal code to pass. Ensure 80%+ coverage.
---

# TDD Command

This command invokes the **tdd-guide** agent to enforce test-driven development methodology with pytest.

## Workflow

```
/tdd [target]
    │
    Step 0: /test-coverage → Get prioritized gap list
    │
    Step 1: Determine work queue
    │       ├─► IF target provided → filter gaps to target
    │       └─► ELSE → use full gap list (by priority)
    │
    For each file in queue:
    │
    Step 2: Does implementation exist?
    │       │
    │       ├─► YES (existing code, missing tests)
    │       │   ├─► Analyze untested code paths
    │       │   ├─► Write tests → Expect PASS
    │       │   └─► IF FAIL → Bug found! Fix code
    │       │
    │       └─► NO (new code)
    │           └─► RED → GREEN → REFACTOR
    │
    Step 3: Verify coverage improved
    │
    Step 4: Next file
```

## When to Use

Use `/tdd` when:
- Implementing new features
- Adding new functions/classes
- Fixing bugs (write test that reproduces bug first)
- Refactoring existing code
- Building critical business logic
- Improving coverage on existing code

## TDD Cycle (for new code)

```
RED → GREEN → REFACTOR → REPEAT

RED:      Write a failing test
GREEN:    Write minimal code to pass
REFACTOR: Improve code, keep tests passing
REPEAT:   Next feature/scenario
```

## Coverage Thresholds

See `/test-coverage` for threshold requirements by code type.

## Example Usage

```
User: /tdd I need a function to validate email addresses

Agent (tdd-guide):
# TDD Session: Email Validator

## Step 1: Define Interface

```python
# app/utils/validators.py
def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    raise NotImplementedError
```

## Step 2: Write Failing Test (RED)

```python
# tests/unit/test_validators.py
import pytest
from app.utils.validators import is_valid_email


class TestEmailValidator:
    def test_valid_email_returns_true(self):
        assert is_valid_email("user@example.com") is True

    def test_invalid_email_returns_false(self):
        assert is_valid_email("invalid-email") is False

    def test_email_with_subdomain(self):
        assert is_valid_email("user@sub.example.com") is True

    @pytest.mark.parametrize("email", [
        "",
        "no-at-sign",
        "@no-local-part.com",
        "no-domain@",
        None,
    ])
    def test_invalid_emails(self, email):
        assert is_valid_email(email) is False
```

## Step 3: Run Tests - Verify FAIL

```bash
pytest tests/unit/test_validators.py -v

FAILED tests/unit/test_validators.py::TestEmailValidator::test_valid_email
NotImplementedError
```

✅ Tests fail as expected. Ready to implement.

## Step 4: Implement Minimal Code (GREEN)

```python
# app/utils/validators.py
import re

def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    if email is None or not isinstance(email, str):
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

## Step 5: Run Tests - Verify PASS

```bash
pytest tests/unit/test_validators.py -v

PASSED tests/unit/test_validators.py::TestEmailValidator::test_valid_email
PASSED tests/unit/test_validators.py::TestEmailValidator::test_invalid_email
...
5 passed
```

✅ All tests passing!

## Step 6: Check Coverage

```bash
pytest --cov=app.utils.validators tests/unit/test_validators.py

Coverage: 100% ✅
```
```

## Commands

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_validators.py -v

# Run tests matching pattern
pytest -k "test_email" -v

# Watch mode (requires pytest-watch)
ptw tests/
```

## Coverage Requirements

See `/test-coverage` for detailed thresholds. Summary:
- **80% minimum** for all code
- **100% required** for security-critical code

## TDD Best Practices

**DO:**
- ✅ Write the test FIRST, before any implementation
- ✅ Run tests and verify they FAIL before implementing
- ✅ Write minimal code to make tests pass
- ✅ Refactor only after tests are green
- ✅ Add edge cases and error scenarios

**DON'T:**
- ❌ Write implementation before tests
- ❌ Skip running tests after each change
- ❌ Write too much code at once
- ❌ Ignore failing tests
- ❌ Test implementation details

## Composition

This command follows the **Pipeline Pattern**:

```
/tdd
    │
    ├─► /test-coverage        ← Delegation: gap analysis
    │   (returns prioritized file list)
    │
    └─► For each file:
        ├─► tdd-guide agent   ← TDD cycle
        └─► /test-coverage    ← Verify improvement
```

**Delegates to:**
- `/test-coverage` - Identifies which files need tests and their priority

**Invokes:** The **tdd-guide** agent for the actual TDD workflow.
