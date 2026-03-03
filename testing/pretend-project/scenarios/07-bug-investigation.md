# Scenario 07: Bug Investigation

## Features Exercised

- Commands: `/bug`, `/bug-swarm`
- Skills: bug-investigate
- Agents: (multiple, via bug-swarm)

## Prerequisites

Scenario 04 completed (auth module exists with tests). Ideally run after
some implementation is in place so the bug has realistic context.

## Setup

The scaffold includes a planted bug: the User model's `set_password` method
has no password strength validation, and the `check_password` method works
correctly but there's no account lockout after failed attempts. Additionally,
the db_health endpoint in health.py claims the database is connected without
actually checking.

For this scenario, imagine a tester reports: "I can register with a 1-
character password and the API accepts it. Also, the health endpoint says
the database is connected even when it isn't."

## Prompts

### Prompt 07-A: Single Bug Investigation

```text
A tester reports: "The /api/auth/register endpoint accepts a password of '1'
with no error. Passwords should require at least 8 characters, a number, and
a special character."

Investigate this bug and fix it.

Use /bug to run a hypothesis-driven investigation.
```

**What Should Happen:**
- Claude invokes `/bug` which triggers the bug-investigate skill.
- Hypothesis-driven investigation:
  1. Hypothesis: set_password has no validation
  2. Evidence: reads user.py, confirms no password strength check
  3. Root cause: set_password accepts any string
  4. Fix: add password validation in set_password or the auth service
  5. Test: write a regression test
- Tracks provenance: which files were read, what evidence supports the
  conclusion.
- Follows the RED → GREEN → REFACTOR pattern for the fix.

**Checkpoint:** Bug is found (user.py:16 — no validation). Fix implemented.
Regression test written and passing. Investigation log shows hypothesis
chain.

---

### Prompt 07-B: Bug Swarm

```text
There are two bugs reported:
1. The /health/db endpoint says "connected" without checking the database
2. After registering a user, the login endpoint sometimes returns 500

Investigate both in parallel.

Use /bug-swarm with 3 hypotheses.
```

**What Should Happen:**
- Claude invokes `/bug-swarm` which spawns multiple agents to investigate
  in parallel.
- Bug 1 investigation:
  - Agent reads health.py, confirms the TODO and hardcoded response
  - Fix: implement actual database health check
- Bug 2 investigation:
  - Agent traces the login flow
  - Hypotheses: password hash mismatch, missing database commit after
    register, session handling issue
  - Root cause identified (may be a race condition or missing db.commit)
- Multiple hypotheses are explored simultaneously.
- Each agent reports findings. Results are consolidated.

**Checkpoint:** Both bugs identified with root causes. Fixes proposed or
implemented. Each bug has a regression test. The swarm explored at least 3
hypotheses total.

---

### Prompt 07-C: Verify Fixes

```text
Run the tests to confirm both bug fixes don't break anything.
```

**What Should Happen:**
- Claude runs pytest. All existing tests pass plus the new regression tests.

**Checkpoint:** Test suite passes. Coverage increased from new tests.
