---
name: tdd-workflow
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with pytest and 80%+ coverage.
model: opus
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Test-Driven Development Workflow

This skill ensures all code development follows TDD principles with comprehensive test coverage using pytest.

## When to Activate

- Writing new features or functionality
- Fixing bugs or issues
- Refactoring existing code
- Adding API endpoints
- Creating new Flask blueprints or models

## Core Principles

### 1. Tests BEFORE Code
ALWAYS write tests first, then implement code to make tests pass.

### 2. Coverage Requirements
- Minimum 80% coverage (unit + integration + E2E)
- All edge cases covered
- Error scenarios tested
- Boundary conditions verified

### 3. Test Types

#### Unit Tests
- Individual functions and utilities
- Model methods and properties
- Service layer logic
- Helper functions

#### Integration Tests
- API endpoints
- Database operations
- Service interactions
- External API calls

#### E2E Tests (Playwright)
- Critical user flows
- Complete workflows
- Browser automation
- UI interactions

## TDD Workflow Steps

### Step 1: Write User Journeys
```
As a [role], I want to [action], so that [benefit]

Example:
As a user, I want to search for markets semantically,
so that I can find relevant markets even without exact keywords.
```

### Step 2: Generate Test Cases

```python
# tests/unit/test_market_service.py

import pytest
from app.services.market_service import MarketService

class TestSemanticSearch:
    def test_returns_relevant_markets_for_query(self, mock_embedding_service):
        """Search returns markets relevant to the query."""
        service = MarketService()

        results = service.search_markets("election results")

        assert len(results) > 0
        assert any("election" in m.name.lower() for m in results)

    def test_handles_empty_query_gracefully(self):
        """Empty query returns empty results without error."""
        service = MarketService()

        results = service.search_markets("")

        assert results == []

    def test_falls_back_to_substring_when_redis_unavailable(
        self, mock_redis_down
    ):
        """Falls back to substring search when Redis is unavailable."""
        service = MarketService()

        results = service.search_markets("election")

        assert len(results) > 0  # Still works

    def test_sorts_results_by_similarity_score(self, mock_embedding_service):
        """Results are sorted by similarity score descending."""
        service = MarketService()

        results = service.search_markets("election")

        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)
```

### Step 3: Run Tests (They Should Fail)
```bash
pytest tests/unit/test_market_service.py -v
# Tests should fail - we haven't implemented yet
```

### Step 4: Implement Code
Write minimal code to make tests pass:

```python
# app/services/market_service.py

from typing import Optional
from app.models import Market
from app.rag import generate_embedding, vector_search
from app import redis_client

class MarketService:
    def search_markets(
        self,
        query: str,
        *,
        limit: int = 10
    ) -> list[Market]:
        if not query:
            return []

        # Try vector search first
        if redis_client.ping():
            embedding = generate_embedding(query)
            return vector_search(embedding, limit=limit)

        # Fallback to substring search
        return Market.query.filter(
            Market.name.ilike(f'%{query}%')
        ).limit(limit).all()
```

### Step 5: Run Tests Again
```bash
pytest tests/unit/test_market_service.py -v
# Tests should now pass
```

### Step 6: Refactor
Improve code quality while keeping tests green:
- Remove duplication
- Improve naming
- Optimize performance
- Enhance readability

### Step 7: Verify Coverage
```bash
pytest --cov=app --cov-report=term-missing
# Verify 80%+ coverage achieved
```

## Testing Patterns

### Unit Test Pattern (pytest)

```python
import pytest
from app.models import User

class TestUserModel:
    def test_creates_user_with_valid_data(self, db_session):
        """User is created with valid data."""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"

    def test_requires_unique_email(self, db_session, existing_user):
        """Duplicate email raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        duplicate = User(
            email=existing_user.email,
            name="Duplicate"
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_password_is_hashed(self, db_session):
        """Password is stored as hash, not plaintext."""
        user = User(email="test@example.com")
        user.set_password("secret123")

        assert user.password_hash != "secret123"
        assert user.check_password("secret123")
```

### API Integration Test Pattern

```python
# tests/integration/test_markets_api.py

import pytest
from flask import url_for

class TestMarketsAPI:
    def test_list_markets_returns_200(self, client):
        """GET /api/markets returns 200."""
        response = client.get('/api/markets')

        assert response.status_code == 200
        assert response.json['success'] is True
        assert isinstance(response.json['data'], list)

    def test_validates_query_parameters(self, client):
        """Invalid query params return 400."""
        response = client.get('/api/markets?limit=invalid')

        assert response.status_code == 400

    def test_create_requires_authentication(self, client):
        """POST /api/markets requires auth."""
        response = client.post('/api/markets', json={
            'name': 'Test Market'
        })

        assert response.status_code == 401

    def test_create_market_with_valid_data(self, auth_client):
        """POST /api/markets creates market."""
        response = auth_client.post('/api/markets', json={
            'name': 'Test Market',
            'description': 'A test market',
            'end_date': '2025-12-31'
        })

        assert response.status_code == 201
        assert response.json['data']['name'] == 'Test Market'
```

### E2E Test Pattern (Playwright)

```python
# tests/e2e/test_login_flow.py

import pytest
from playwright.sync_api import Page, expect

class TestLoginFlow:
    def test_user_can_login_and_view_dashboard(self, page: Page):
        """User can login and access dashboard."""
        # Navigate to login
        page.goto("/auth/login")
        expect(page).to_have_title("Login")

        # Fill login form
        page.locator('[data-testid="email-input"]').fill("test@example.com")
        page.locator('[data-testid="password-input"]').fill("password123")
        page.locator('[data-testid="login-button"]').click()

        # Verify redirect to dashboard
        expect(page).to_have_url(".*dashboard.*")
        expect(page.locator('[data-testid="user-menu"]')).to_be_visible()

        # Take screenshot
        page.screenshot(path="artifacts/dashboard.png")

    def test_invalid_login_shows_error(self, page: Page):
        """Invalid credentials show error message."""
        page.goto("/auth/login")

        page.locator('[data-testid="email-input"]').fill("wrong@example.com")
        page.locator('[data-testid="password-input"]').fill("wrongpassword")
        page.locator('[data-testid="login-button"]').click()

        # Verify error message
        expect(page.locator('[data-testid="error-message"]')).to_be_visible()
        expect(page.locator('[data-testid="error-message"]')).to_contain_text(
            "Invalid"
        )
```

## Test File Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_models.py       # Model unit tests
│   ├── test_services.py     # Service layer tests
│   └── test_utils.py        # Utility function tests
├── integration/
│   ├── test_auth_api.py     # Auth endpoint tests
│   ├── test_markets_api.py  # Markets endpoint tests
│   └── test_database.py     # Database integration tests
└── e2e/
    ├── conftest.py          # Playwright fixtures
    ├── test_auth_flow.py    # Auth E2E tests
    └── test_market_flow.py  # Market E2E tests
```

## Fixtures (conftest.py)

```python
# tests/conftest.py

import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """Database session for testing."""
    with app.app_context():
        yield db.session

@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(email="test@example.com", name="Test User")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_client(client, test_user):
    """Authenticated test client."""
    response = client.post('/auth/login', json={
        'email': test_user.email,
        'password': 'password123'
    })
    token = response.json['token']
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client

@pytest.fixture
def mock_redis_down(mocker):
    """Mock Redis being unavailable."""
    mocker.patch('app.redis_client.ping', return_value=False)
```

## Common Testing Mistakes to Avoid

### WRONG: Testing Implementation Details
```python
# Don't test internal state
assert user._password_hash.startswith('$2b$')
```

### CORRECT: Test User-Visible Behavior
```python
# Test what users see
assert user.check_password("secret123")
```

### WRONG: No Test Isolation
```python
# Tests depend on each other
def test_creates_user():
    User.create(email="test@example.com")

def test_updates_same_user():
    user = User.query.filter_by(email="test@example.com").first()
```

### CORRECT: Independent Tests
```python
# Each test sets up its own data
def test_creates_user(db_session):
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None

def test_updates_user(db_session, test_user):
    test_user.name = "Updated"
    db_session.commit()
    assert test_user.name == "Updated"
```

## Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_models.py -v

# Run tests matching pattern
pytest -k "test_login" -v

# Run with parallel execution
pytest -n auto

# Watch mode (with pytest-watch)
ptw tests/

# E2E tests with headed browser
pytest tests/e2e/ --headed

# Generate HTML coverage report
pytest --cov=app --cov-report=html
```

## Success Metrics

- 80%+ code coverage achieved
- All tests passing (green)
- No skipped or disabled tests
- Fast test execution (< 30s for unit tests)
- E2E tests cover critical user flows
- Tests catch bugs before production

---

**Remember**: Tests are not optional. They are the safety net that enables confident refactoring, rapid development, and production reliability.
