# Scenario 04: Test-Driven Development

## Features Exercised

- Commands: `/tdd`, `/verify quick`, `/checkpoint`, `/catalog query`
- Skills: tdd-workflow, testing-strategy, find-patterns
- Agents: tdd-guide
- Hooks: post-python-format (auto), post_task (auto)

## Prerequisites

Scenario 03 completed (worktrees created). Working in the auth worktree.

## Prompts

### Prompt 04-A: Start TDD for Auth

```text
I want to build the user registration endpoint using TDD. Start with the
tests. The endpoint should be POST /api/auth/register accepting email,
username, and password. It should return 201 on success and 400 on validation
errors.

Use /tdd to guide me through this.
```

**What Should Happen:**
- Claude invokes `/tdd` which triggers the tdd-workflow skill and may spawn
  the tdd-guide agent.
- Phase 1 (RED): Writes failing tests first:
  - test_register_user_with_valid_data
  - test_register_user_with_missing_email
  - test_register_user_with_duplicate_username
  - test_register_user_with_weak_password
- Test naming follows the standard: `test_<subject>_<preposition>_<scenario>`
- Runs the tests — they all fail (RED phase).
- The post-python-format hook auto-formats new Python files.

**Checkpoint:** Tests exist in `tests/test_auth.py`. All tests fail with
clear error messages. Tests follow naming conventions.

---

### Prompt 04-B: Implement to Pass Tests

```text
Now implement the registration endpoint to make all the tests pass. Follow
the GREEN phase — minimal code to pass, nothing more.
```

**What Should Happen:**
- Claude continues the TDD workflow (GREEN phase).
- Creates `src/taskhive/routes/auth.py` with the registration endpoint.
- Creates `src/taskhive/services/auth_service.py` with registration logic.
- Registers the auth blueprint in `app.py`.
- Runs tests — they should pass.
- The post-python-format hook fires on each new Python file.

**Checkpoint:** All registration tests pass. No extra code beyond what's
needed to pass the tests.

---

### Prompt 04-C: Refactor Phase

```text
Tests are green. Now refactor — clean up the auth code. Extract validation
into its own function, improve error messages, add proper HTTP status codes.
Keep all tests passing.
```

**What Should Happen:**
- Claude continues the TDD workflow (REFACTOR phase).
- Extracts password validation, email validation into the service layer.
- Improves error response format.
- Runs tests after each change to confirm they still pass.
- `/verify quick` runs a fast lint + type check.

**Checkpoint:** Code is cleaner. All tests still pass. No regressions.

---

### Prompt 04-D: TDD for Login

```text
Now use /tdd for the login endpoint. POST /api/auth/login accepting email
and password, returning a JWT access token on success, 401 on invalid
credentials.
```

**What Should Happen:**
- Same RED → GREEN → REFACTOR cycle.
- Tests: test_login_user_with_valid_credentials,
  test_login_user_with_wrong_password, test_login_user_with_nonexistent_email.
- Implementation uses flask-jwt-extended to generate tokens.

**Checkpoint:** Login tests pass. JWT token is returned on successful login.

---

### Prompt 04-E: Find Patterns

```text
Are there similar authentication patterns in the codebase I should follow?
```

**What Should Happen:**
- Claude invokes `/find-patterns` or the find-patterns skill.
- Searches for existing patterns (may find the health endpoint pattern,
  blueprint registration, service layer pattern).
- Reports what conventions are already established.

**Checkpoint:** Pattern report identifies existing conventions.

---

### Prompt 04-F: Create Checkpoint

```text
Good progress. Save a checkpoint here so we can verify this state later.

/checkpoint create "auth-complete"
```

**What Should Happen:**
- Claude invokes `/checkpoint create` with a name.
- Creates a checkpoint recording the current state: passing tests, file
  list, coverage numbers.
- It can be verified later with `/checkpoint verify "auth-complete"`.

**Checkpoint:** Checkpoint saved. It can be listed with `/checkpoint list`.

---

### Prompt 04-G: Query Catalog

```text
/catalog query "Where are all the route files?"
```

**What Should Happen:**
- Claude invokes `/catalog query` and searches the file catalog.
- Returns route files, including at least `health.py` and `auth.py`.

**Checkpoint:** Catalog query returns accurate results.
