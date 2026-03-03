# Scenario 05: Verification and Code Quality

## Features Exercised

- Commands: `/verify`, `/verify quick`, `/verify full`, `/verify pre-pr`,
  `/build-fix`, `/ci`, `/test-coverage`
- Skills: verification-loop
- Agents: build-error-resolver

## Prerequisites

Scenario 04 completed (auth module implemented with tests).

## Prompts

### Prompt 05-A: Quick Verification

```text
Run a quick check on the code I've written.
```

**What Should Happen:**
- Claude invokes `/verify quick`.
- Runs: ruff check (lint), ruff format --check (formatting), mypy (types).
- Reports any issues found.
- Likely finds: type annotation gaps (mypy strict mode), possibly unused
  imports or formatting issues.

**Checkpoint:** Verification report with specific issues listed.

---

### Prompt 05-B: Fix Build Errors

```text
There are some type errors and lint issues. Fix them all.

Use /build-fix to handle this.
```

**What Should Happen:**
- Claude invokes `/build-fix` which spawns the build-error-resolver agent.
- The agent iteratively:
  1. Runs ruff and mypy
  2. Reads the errors
  3. Fixes each error
  4. Re-runs to confirm the fix
  5. Repeats until clean
- Adds type annotations where mypy strict requires them.
- Fixes any ruff violations.

**Checkpoint:** `/verify quick` passes clean. No type errors, no lint issues.

---

### Prompt 05-C: Full Verification

```text
/verify full
```

**What Should Happen:**
- Claude invokes `/verify full` which runs the verification-loop skill.
- Full suite: lint, format, types, tests, security scan, coverage.
- Reports results for each check.
- Flags if coverage is below 80% threshold.

**Checkpoint:** Full verification report. All checks pass or issues are
clearly identified.

---

### Prompt 05-D: Test Coverage Analysis

```text
How's our test coverage? What gaps exist?

Use /test-coverage to analyze.
```

**What Should Happen:**
- Claude invokes `/test-coverage`.
- Runs pytest with coverage reporting.
- Identifies untested code paths: probably the config module, error
  handlers, edge cases in auth.
- Suggests specific tests to write for uncovered lines.

**Checkpoint:** Coverage report with percentage and specific uncovered lines
identified. Suggestions for new tests.

---

### Prompt 05-E: Run CI Locally

```text
/ci full
```

**What Should Happen:**
- Claude invokes `/ci full`.
- Runs the same checks that CI would run: lint, format, types, tests,
  coverage threshold.
- Reports pass/fail matching what GitHub Actions would produce.

**Checkpoint:** CI report. All checks pass, or failures match what CI would
catch.

---

### Prompt 05-F: Pre-PR Verification

```text
/verify pre-pr
```

**What Should Happen:**
- Claude invokes `/verify pre-pr` — the most thorough verification level.
- Everything in "full" plus: checks for debug statements, TODO comments,
  print() calls, hardcoded secrets, missing docstrings in public APIs.
- Ensures the code is ready for a pull request.

**Checkpoint:** Pre-PR report. Any issues are blockers that must be fixed
before opening a PR.
