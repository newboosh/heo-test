# Scenario 10: End-to-End Testing

## Features Exercised

- Commands: `/e2e`
- Skills: eval-harness
- Agents: e2e-runner

## Prerequisites

Scenarios 04-05 completed (auth module working, tests passing).

## Prompts

### Prompt 10-A: E2E Test for Auth Flow

```text
Write an end-to-end test for the complete authentication flow:
1. Register a new user
2. Login with those credentials
3. Access a protected endpoint with the JWT token
4. Verify the token expires correctly

Use /e2e to create this.
```

**What Should Happen:**
- Claude invokes `/e2e` which spawns the e2e-runner agent.
- The agent creates end-to-end tests (using pytest or Playwright for API
  testing):
  - Full registration → login → protected access flow
  - Token expiry and refresh behavior
  - Error paths (invalid credentials, expired tokens)
- Tests hit actual endpoints (using Flask test client or a running server).
- The eval-harness skill may structure the test as an evaluation.

**Checkpoint:** E2E test file created. Tests exercise the full auth flow
from registration through protected endpoint access. Tests pass.

---

### Prompt 10-B: E2E Test for Task Workflow

```text
Write end-to-end tests for the task management workflow:
1. Register and login
2. Create a task
3. Assign the task to another user
4. Update task status
5. Verify task appears in listing

Use /e2e to create this.
```

**What Should Happen:**
- Claude invokes `/e2e` for the task workflow.
- Creates tests covering the full task lifecycle.
- Tests demonstrate multi-user interaction patterns.

**Checkpoint:** E2E tests for task workflow pass. Coverage includes both
happy path and error cases.

---

### Prompt 10-C: Eval-Driven Testing (Advanced)

```text
I want to set up evaluations for the API that can be rerun as regression
tests. Use the eval harness to define success criteria and metrics.
```

**What Should Happen:**
- The eval-harness skill creates a structured evaluation framework.
- Defines: test scenarios, success metrics, performance baselines.
- Can be rerun to detect regressions.

**Checkpoint:** Eval configuration created. Baseline results recorded.
