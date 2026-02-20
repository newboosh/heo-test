---
name: eval-harness
description: Eval-Driven Development (EDD) framework for Python. Define success criteria before implementation, run evals continuously, track pass@k metrics.
model: opus
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Eval Harness Skill

A formal evaluation framework for Claude Code sessions, implementing eval-driven development (EDD) principles for Python/Flask projects.

## Philosophy

Eval-Driven Development treats evals as the "unit tests of AI development":
- Define expected behavior BEFORE implementation
- Run evals continuously during development
- Track regressions with each change
- Use pass@k metrics for reliability measurement

## Eval Types

### Capability Evals
Test if the implementation can do something new:

```markdown
[CAPABILITY EVAL: user-authentication]
Task: Implement user login with email/password
Success Criteria:
  - [ ] User can register with valid email/password
  - [ ] Password is hashed with bcrypt/werkzeug
  - [ ] User can login with correct credentials
  - [ ] Invalid credentials return 401
  - [ ] Session is created on successful login
Expected Output: Working /auth/login and /auth/register endpoints
```

### Regression Evals
Ensure changes don't break existing functionality:

```markdown
[REGRESSION EVAL: auth-system]
Baseline: commit abc123
Tests:
  - test_login_success: PASS/FAIL
  - test_login_invalid: PASS/FAIL
  - test_session_persist: PASS/FAIL
Result: X/Y passed (previously Y/Y)
```

## Grader Types

### 1. Code-Based Grader (pytest)
Deterministic checks using tests:

```bash
# Check if specific test passes
pytest tests/test_auth.py::test_user_can_login -v && echo "PASS" || echo "FAIL"

# Check coverage threshold
pytest --cov=app --cov-fail-under=80 && echo "PASS" || echo "FAIL"

# Check types
mypy app/ && echo "PASS" || echo "FAIL"

# Check lint
ruff check app/ && echo "PASS" || echo "FAIL"
```

### 2. Model-Based Grader
Use Claude to evaluate open-ended outputs:

```markdown
[MODEL GRADER PROMPT]
Evaluate the following code change:
1. Does it solve the stated problem?
2. Is it well-structured per Dignified Python rules?
3. Are edge cases handled?
4. Is error handling appropriate (LBYL, no bare except)?
5. Are there security issues?

Score: 1-5 (1=poor, 5=excellent)
Reasoning: [explanation]
```

### 3. Human Grader
Flag for manual review:

```markdown
[HUMAN REVIEW REQUIRED]
Change: Added payment processing endpoint
Reason: Security-critical code requires human verification
Risk Level: HIGH
Checklist:
  - [ ] No sensitive data logged
  - [ ] Input validation complete
  - [ ] Rate limiting configured
  - [ ] PCI compliance verified
```

## Metrics

### pass@k
"At least one success in k attempts"
- **pass@1**: First attempt success rate (target: >70%)
- **pass@3**: Success within 3 attempts (target: >90%)
- Typical target: pass@3 > 90%

### pass^k
"All k trials succeed"
- Higher bar for reliability
- **pass^3**: 3 consecutive successes
- Use for critical paths (auth, payments)

## Eval Workflow

### 1. Define (Before Coding)

```markdown
## EVAL DEFINITION: feature-xyz

### Capability Evals
1. Can create new database record
2. Can validate input with Marshmallow schema
3. Can return proper error responses
4. Can handle concurrent requests

### Regression Evals
1. Existing API endpoints unchanged
2. Database migrations reversible
3. Test suite still passes

### Success Metrics
- pass@3 > 90% for capability evals
- pass^3 = 100% for regression evals
- Coverage >= 80%
```

### 2. Implement
Write code to pass the defined evals.

### 3. Evaluate

```bash
# Run capability evals
pytest tests/test_feature_xyz.py -v --tb=short

# Run regression evals
pytest tests/ -v --ignore=tests/test_feature_xyz.py

# Check coverage
pytest --cov=app --cov-report=term-missing

# Generate report
```

### 4. Report

```markdown
EVAL REPORT: feature-xyz
========================

Capability Evals:
  create-record:     PASS (pass@1)
  validate-input:    PASS (pass@2)
  error-responses:   PASS (pass@1)
  concurrency:       PASS (pass@3)
  Overall:           4/4 passed

Regression Evals:
  api-endpoints:     PASS
  migrations:        PASS
  test-suite:        PASS
  Overall:           3/3 passed

Metrics:
  pass@1: 75% (3/4)
  pass@3: 100% (4/4)
  Coverage: 87%

Status: READY FOR REVIEW
```

## Eval Storage

Store evals in project:

```
.claude/
  evals/
    feature-xyz.md      # Eval definition
    feature-xyz.log     # Eval run history
    baseline.json       # Regression baselines
```

## Example: Adding User Profile Feature

```markdown
## EVAL: user-profile-api

### Phase 1: Define (10 min)

Capability Evals:
- [ ] GET /api/profile returns current user data
- [ ] PATCH /api/profile updates allowed fields
- [ ] Cannot update email without verification
- [ ] Cannot update other users' profiles
- [ ] Returns 401 for unauthenticated requests

Regression Evals:
- [ ] Existing auth endpoints work
- [ ] User model unchanged for existing fields
- [ ] Session handling intact

### Phase 2: Implement (varies)

```python
# tests/test_profile.py - Write tests FIRST
class TestUserProfile:
    def test_get_profile_returns_user_data(self, auth_client, test_user):
        response = auth_client.get('/api/profile')
        assert response.status_code == 200
        assert response.json['email'] == test_user.email

    def test_patch_profile_updates_name(self, auth_client):
        response = auth_client.patch('/api/profile', json={'name': 'New Name'})
        assert response.status_code == 200
        assert response.json['name'] == 'New Name'

    def test_cannot_update_other_user(self, auth_client, other_user):
        response = auth_client.patch(f'/api/users/{other_user.id}', json={'name': 'Hacked'})
        assert response.status_code == 403
```

### Phase 3: Evaluate

```bash
# Run all profile tests
pytest tests/test_profile.py -v

# Run regression tests
pytest tests/test_auth.py tests/test_users.py -v

# Check coverage
pytest --cov=app/api/profile --cov-fail-under=80
```

### Phase 4: Report

EVAL REPORT: user-profile-api
==============================
Capability: 5/5 passed (pass@3: 100%)
Regression: 3/3 passed (pass^3: 100%)
Coverage: 92%
Status: SHIP IT
```

## Integration with TDD

EDD complements TDD:

| TDD | EDD |
|-----|-----|
| Unit/integration tests | Capability + regression evals |
| Test before code | Eval definition before code |
| Green/red/refactor | Pass/fail/iterate |
| Code coverage | pass@k metrics |

## Best Practices

1. **Define evals BEFORE coding** - Forces clear thinking about success criteria
2. **Run evals frequently** - Catch regressions early
3. **Track pass@k over time** - Monitor reliability trends
4. **Use pytest for code graders** - Deterministic > probabilistic
5. **Human review for security** - Never fully automate security checks
6. **Keep evals fast** - Slow evals don't get run (<30s ideal)
7. **Version evals with code** - Evals are first-class artifacts
8. **Separate capability from regression** - Different failure modes

## Commands

```bash
# Define new eval
# Creates .claude/evals/feature-name.md
/eval define feature-name

# Check current eval status
/eval check feature-name

# Generate full report
/eval report feature-name

# Run all evals
pytest tests/ -v --tb=short && echo "ALL EVALS PASS"
```
