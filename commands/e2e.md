---
description: Generate and run end-to-end tests with Playwright. Creates test journeys, runs tests, captures screenshots/videos/traces.
---

# E2E Command

This command invokes the **e2e-runner** agent to generate, maintain, and execute end-to-end tests using Playwright with pytest.

## What This Command Does

1. **Generate Test Journeys** - Create Playwright tests for user flows
2. **Run E2E Tests** - Execute tests across browsers
3. **Capture Artifacts** - Screenshots, videos, traces on failures
4. **Identify Flaky Tests** - Quarantine unstable tests

## When to Use

Use `/e2e` when:
- Testing critical user journeys (login, forms, workflows)
- Verifying multi-step flows work end-to-end
- Testing UI interactions and navigation
- Validating integration between frontend and backend
- Preparing for production deployment

## Example Usage

```
User: /e2e Test the login and dashboard flow

Agent (e2e-runner):
# E2E Test Generation: Login and Dashboard Flow

## Generated Test

```python
# tests/e2e/test_login_flow.py
import pytest
from playwright.sync_api import Page, expect


class TestLoginFlow:
    def test_user_can_login_and_view_dashboard(self, page: Page):
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
        page.goto("/auth/login")

        page.locator('[data-testid="email-input"]').fill("wrong@example.com")
        page.locator('[data-testid="password-input"]').fill("wrongpassword")
        page.locator('[data-testid="login-button"]').click()

        # Verify error message
        expect(page.locator('[data-testid="error-message"]')).to_be_visible()
        expect(page.locator('[data-testid="error-message"]')).to_contain_text("Invalid")
```
```

## Commands

```bash
# Install Playwright
pip install pytest-playwright
playwright install

# Run all E2E tests
pytest tests/e2e/ -v

# Run with browser visible
pytest tests/e2e/ --headed

# Run specific test file
pytest tests/e2e/test_login_flow.py -v

# Generate test code interactively
playwright codegen http://localhost:5000

# Run with tracing
pytest tests/e2e/ --tracing on

# View trace
playwright show-trace test-results/trace.zip
```

## Test Structure

```
tests/
├── e2e/
│   ├── conftest.py        # Fixtures
│   ├── test_auth.py       # Auth flows
│   ├── test_dashboard.py  # Dashboard flows
│   └── test_search.py     # Search flows
└── pages/                 # Page Objects
    ├── login_page.py
    └── dashboard_page.py
```

## Artifacts

On test failure:
- Screenshot of failing state
- Video recording
- Trace file for debugging

```bash
# View artifacts
ls test-results/
```

## Critical Flows to Test

**HIGH Priority:**
1. User login/logout
2. User registration
3. Password reset
4. Core CRUD operations
5. Search functionality

**MEDIUM Priority:**
1. Settings updates
2. File uploads
3. Export/download
4. Error handling

## Best Practices

**DO:**
- ✅ Use `data-testid` attributes for selectors
- ✅ Wait for API responses, not arbitrary timeouts
- ✅ Use Page Object Model for maintainability
- ✅ Test critical user journeys

**DON'T:**
- ❌ Use brittle CSS selectors
- ❌ Use `time.sleep()` for waits
- ❌ Test against production
- ❌ Ignore flaky tests

Invokes the **e2e-runner** agent.
