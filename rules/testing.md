# Testing Requirements

## Test-Driven Development (TDD)

TDD is the **mandatory workflow** for this project.

### The TDD Cycle

```
RED → GREEN → REFACTOR
```

1. **RED**: Write a failing test first
   - Test should fail for the right reason
   - Test should be specific and focused
   - Test should document expected behavior

2. **GREEN**: Write minimal code to pass
   - Only write enough code to make the test pass
   - Don't optimize or add extra features
   - Resist the urge to write "complete" solution

3. **REFACTOR**: Improve the code
   - Clean up duplication
   - Improve naming
   - Simplify logic
   - Tests must still pass

### TDD Workflow Example

```python
# Step 1: RED - Write failing test
def test_user_can_reset_password():
    user = User(email="test@example.com")
    token = user.generate_reset_token()

    assert token is not None
    assert len(token) == 64
    assert user.verify_reset_token(token) is True

# Step 2: Run test - it FAILS (no implementation yet)
# pytest tests/test_auth.py::test_user_can_reset_password -v

# Step 3: GREEN - Write minimal implementation
class User:
    def generate_reset_token(self):
        self._reset_token = secrets.token_hex(32)
        return self._reset_token

    def verify_reset_token(self, token):
        return token == self._reset_token

# Step 4: Run test - it PASSES

# Step 5: REFACTOR - Add expiration, hashing, etc.
```

## Minimum Test Coverage: 80%

Check coverage with:
```bash
pytest --cov=app --cov-report=term-missing
```

## Test Types

### 1. Unit Tests (Required)
- Test individual functions and classes
- Mock external dependencies
- Fast execution (<100ms per test)

```python
def test_email_validation():
    assert is_valid_email("user@example.com") is True
    assert is_valid_email("invalid-email") is False
```

### 2. Integration Tests (Required)
- Test API endpoints
- Test database operations
- Use test database/fixtures

```python
def test_create_user_endpoint(client, db):
    response = client.post("/api/users", json={
        "email": "new@example.com",
        "password": "secure123"
    })
    assert response.status_code == 201
    assert User.query.filter_by(email="new@example.com").first() is not None
```

### 3. End-to-End Tests (Critical Flows)
- Test complete user journeys
- Use Playwright or Selenium
- Focus on critical paths: login, checkout, etc.

## Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_validators.py
├── integration/
│   ├── test_api_auth.py
│   ├── test_api_users.py
│   └── test_database.py
└── e2e/
    ├── test_login_flow.py
    └── test_checkout_flow.py
```

## Fixtures (conftest.py)

```python
import pytest
from app import create_app, db as _db

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    return _db

@pytest.fixture
def user(db):
    user = User(email="test@example.com")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user
```

## Running Tests

```bash
# Run all tests
make test-parallel

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v

# Run tests matching pattern
pytest -k "test_user" -v

# Run and stop on first failure
pytest -x

# Run with verbose output
pytest -v --tb=short
```

## Troubleshooting Test Failures

1. **Isolate the failing test**: Run it alone with `-v`
2. **Check fixtures**: Ensure test isolation (no shared state)
3. **Verify mocks**: Are they mocking the right things?
4. **Read the assertion**: What exactly failed?
5. **Fix implementation, not tests** (unless tests are wrong)

## Agent Support

- **tdd-guide agent**: Use PROACTIVELY when implementing new features
- Enforces write-tests-first discipline
- Helps structure test cases

## Quality Checklist

Before marking work complete:
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All tests pass
- [ ] Coverage >= 80%
- [ ] No skipped tests without reason
- [ ] Tests are readable and document behavior
- [ ] Edge cases covered
- [ ] Error conditions tested
