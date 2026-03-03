# Scenario 06: Code Review and Security

## Features Exercised

- Commands: `/code-review`, `/qa`, `/security-review` (as command)
- Skills: security-review, compliance-check, artifact-audit, diff-review
- Agents: code-reviewer, security-reviewer, qa-agent
- Hooks: pre-git-safety-check (auto)

## Prerequisites

Scenario 05 completed (code verified, build clean).

## Prompts

### Prompt 06-A: Code Review

```text
Review all the code I've written in this worktree. Check for quality issues,
potential bugs, and adherence to project standards.

Use /code-review.
```

**What Should Happen:**
- Claude invokes `/code-review` which spawns the code-reviewer agent.
- The agent reviews all uncommitted/changed files:
  - Quality: function complexity, naming, separation of concerns
  - Patterns: consistency with existing conventions
  - Bugs: logic errors, edge cases, error handling gaps
  - Standards: compliance with project standards (from /setup in scenario 00)
- Produces a structured review with severity levels (critical, warning, info).

**Checkpoint:** Review output with specific findings. Should catch at least:
the missing password strength validation noted in user.py, any hardcoded
secrets in config.

---

### Prompt 06-B: Security Review

```text
Do a thorough security review of the authentication module. Check for OWASP
top 10 vulnerabilities, JWT misconfiguration, password handling issues.

Use /security-review.
```

**What Should Happen:**
- Claude invokes the security-review command which spawns the
  security-reviewer agent.
- Focused security analysis:
  - Password handling: no strength validation (planted bug in user.py)
  - JWT configuration: token expiry, algorithm, secret key strength
  - Input validation: SQL injection potential, XSS in responses
  - Authentication bypass: missing rate limiting on login
  - Hardcoded secrets: dev secrets in config.py and app.py
- Produces findings with severity and remediation advice.

**Checkpoint:** Security report flags: weak password policy, hardcoded JWT
secret, missing rate limiting, no token refresh mechanism. Each finding has a
fix recommendation.

---

### Prompt 06-C: QA Validation

```text
/qa src/taskhive/ --staged
```

**What Should Happen:**
- Claude invokes `/qa` which spawns the qa-agent.
- QA validation of staged changes:
  - Artifact audit: tests exist for new code, docs updated
  - Integration points: blueprint registered, models imported
  - Data integrity: migrations needed for new models

**Checkpoint:** QA report identifies missing or incomplete artifacts.

---

### Prompt 06-D: Compliance Check

```text
Check if this code complies with our project standards.
```

**What Should Happen:**
- The compliance-check skill runs against project-standards.yaml
  (created by `/setup` in scenario 00).
- Checks naming conventions, file organization, docstring presence,
  test coverage requirements.

**Checkpoint:** Compliance report with pass/fail per standard.

---

### Prompt 06-E: Diff Review

```text
Review just the changes I've made since the last commit.
```

**What Should Happen:**
- The diff-review skill examines only the git diff.
- Provides focused feedback on recent changes.

**Checkpoint:** Diff-specific review output.

---

### Prompt 06-F: Git Safety Hook Test

```text
Let me try pushing directly to main to verify the safety check works.
```

**What Should Happen:**
- If the user or Claude attempts `git push origin main`, the
  pre-git-safety-check hook blocks it.
- The hook prevents: direct push to main, --no-verify, reset --hard.
- Claude should explain why the push was blocked and suggest using a
  feature branch + PR instead.

**Checkpoint:** Push to main is blocked with a clear error message.

---

### Prompt 06-G: Artifact Audit

```text
Before I create a PR, verify that all required artifacts exist — tests,
documentation, migrations if needed.
```

**What Should Happen:**
- The artifact-audit skill checks:
  - Tests exist for all new modules
  - Documentation updated for new endpoints
  - Database migrations created if models changed
  - CHANGELOG updated (if one exists)

**Checkpoint:** Audit report listing present and missing artifacts.
