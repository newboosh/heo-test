# Testing Standards

Canonical specifications for testing. References authoritative standards where applicable.

---

## Test Pyramid

**Reference:** *Succeeding with Agile* (Cohn, 2009); Google Testing Blog

```
      /  E2E   \     Few, slow, expensive
     / Integration \  Some, moderate
    /     Unit      \ Many, fast, cheap
```

| Type | Coverage Target | Minimum |
|------|-----------------|---------|
| Unit | 80% line | 70% |
| Integration | Critical paths | All endpoints |
| E2E | Happy paths | Core journeys |

---

## Unit Testing

**Framework:** pytest
**Reference:** pytest documentation; *xUnit Test Patterns* (Meszaros, 2007)

### Structure: AAA Pattern
```python
def test_user_creation():
    # Arrange
    data = {"email": "test@example.com"}

    # Act
    result = create_user(data)

    # Assert
    assert result.email == "test@example.com"
```

### Naming
| Element | Convention |
|---------|------------|
| File | `test_<module>.py` |
| Class | `Test<Feature>` |
| Method | `test_<scenario>` |

### Mocking
**Reference:** *Growing Object-Oriented Software, Guided by Tests* (Freeman & Pryce, 2009)

- Mock at boundaries, not internals
- Use `spec=` to catch interface changes
- Prefer dependency injection over patching

---

## Integration Testing

**Framework:** pytest + test database
**Reference:** *Continuous Delivery* (Humble & Farley, 2010)

### Required Tests Per Endpoint
- [ ] Happy path (success)
- [ ] Authentication (401)
- [ ] Authorization (403)
- [ ] Validation (400)
- [ ] Not found (404)

---

## E2E Testing

**Framework:** pytest + Playwright
**Reference:** Playwright documentation; Page Object Model pattern

### Selector Priority
1. `data-testid` attribute (preferred)
2. ARIA roles (`role="button"`)
3. Text content
4. CSS selectors (last resort)

### Page Object Model
```python
class LoginPage:
    def __init__(self, page):
        self.email = page.locator('[data-testid="email"]')
        self.submit = page.locator('[data-testid="submit"]')
```

---

## Test Data

**Reference:** *Working Effectively with Unit Tests* (Fields, 2014)

- **Deterministic:** Same input → same result
- **Isolated:** No shared mutable state
- **Realistic:** Plausible values
- **Minimal:** Only necessary fields

---

## CI Requirements

**Reference:** IEEE 1012-2016 (Software Verification and Validation)

- All unit tests pass
- All integration tests pass
- Coverage meets threshold
- No flaky tests (quarantine within 48h)

---

## Verification Checklist

- [ ] AAA pattern followed
- [ ] Meaningful assertions
- [ ] Edge cases covered
- [ ] Error cases tested
- [ ] No flaky patterns (arbitrary sleeps, race conditions)
- [ ] Mocking at boundaries only
