---
name: gate-decision
description: Automated go/no-go decision criteria for the sprint pipeline. Aggregates signals from code review, QA, security review, and sentinel to produce SHIP / REVISE / BLOCKED. Used by the orchestrate command at Phase 10 (before PR creation).
model: opus
allowed-tools: Read, Grep, Glob
---

# Gate Decision Skill

**You are making a ship/no-ship decision.** Read the review handoff files, evaluate each signal against the criteria below, and produce a verdict. This decision gates whether the code is ready to submit as a pull request.

## When to Use

This skill is consumed by `commands/orchestrate.md` during Phase 10 (Pull Request & CI). It runs before the PR is created. It is not invoked directly by the user.

**Lifecycle context:** See `docs/SPRINT_LIFECYCLE.md`, Phase 10.

## Inputs

Read these files from `.sprint/` (plus `.sentinel/report.md` if present):

| File | Phase | Contains |
|------|-------|----------|
| `.sprint/review-code.yaml` | 7 | Code review findings, approval status |
| `.sprint/qa-report.yaml` | 8 | Test results, coverage, lint, type check, acceptance criteria |
| `.sprint/review-security.yaml` | 9 | Security findings, severity ratings |
| `.sentinel/report.md` | — | Emerging issues: workarounds, mocks, temp code, disconnected features |

If any input file is missing, treat that signal as `BLOCKED` with reason "Phase N handoff missing."

**Note:** `.sentinel/report.md` is optional. If missing, treat `sentinel.pass` as `true` (no emerging issues detected). If present, parse the BLOCKING section to determine if sentinel issues should affect the verdict.

**Scoping:** The sentinel system uses diff-scoped detection — auto-detected issues are limited to lines actually added or modified in this branch, and the consolidation agent only analyzes new code. This means sentinel findings represent issues introduced by the current work, not pre-existing debt in touched files.

## Sentinel Timing

The sentinel system runs **continuously during development** (via PostToolUse hooks on Edit/Write operations) and produces `.sentinel/report.md` as a living document. By the time the gate decision runs at Phase 10, the sentinel report reflects all issues detected across the entire sprint, not just a point-in-time scan. This means the gate reads an already-complete sentinel picture rather than triggering a new scan.

## Decision Process

In autonomous mode, the entire decision process runs without human input. The computed verdict is final. In attended mode, the verdict can be overridden (see Manual Override section).

### Step 1: Extract Signals

For each input file, extract:

```yaml
code_review:
  pass: <all reviews approved, no unresolved blockers>
  unresolved_issues: <count of open review comments>
  severity_max: info|warning|error|critical

qa:
  pass: <all tests passing, lint/type check clean, criteria met>
  tests_passing: <count>
  tests_total: <count>
  coverage: <percentage>
  lint_clean: true|false
  type_check_clean: true|false
  acceptance_criteria_met: <count>
  acceptance_criteria_total: <count>

security_review:
  pass: <no findings above threshold>
  vulnerabilities: <count>
  severity_max: none|low|medium|high|critical

sentinel:
  pass: <BLOCKING section is empty>
  blocking_count: <count of items in BLOCKING section>
  total_issues: <total issues across all sections>
  has_report: true|false
```

### Step 2: Evaluate Verdict

Apply criteria in this order (first match wins):

**BLOCKED** — Any of these is true:
- `security_review.severity_max` is `critical` or `high`
- `qa.tests_passing` < `qa.tests_total`
- `code_review.severity_max` is `critical`
- `sentinel.blocking_count` > 0 (hardcoded secrets, critical mocks, etc.)
- Any required input file is missing

**REVISE** — Any of these is true:
- `code_review.unresolved_issues` > 0 (non-critical)
- `qa.coverage` < `coverage_minimum` from config (default: 80%)
- `qa.lint_clean` is `false` or `qa.type_check_clean` is `false`
- `security_review.severity_max` is `medium` or `low`
- `qa.acceptance_criteria_met` < `qa.acceptance_criteria_total`
- `sentinel.total_issues` > 0 and `sentinel.blocking_count` == 0 (non-blocking emerging issues)

**SHIP** — All of these are true:
- `code_review.pass` is `true`
- `qa.pass` is `true`
- `security_review.pass` is `true`
- `sentinel.pass` is `true` (or no sentinel report exists)

### Step 3: Determine Action

| Verdict | Action |
|---------|--------|
| `SHIP` | Create pull request. Push branch, open PR, run CI on GitHub. |
| `REVISE` | Return to Phase 6 with findings attached. The orchestrate command loops. |
| `BLOCKED` | Halt the sprint. Report blockers. Require manual intervention. |

### Step 4: Write Decision

Write the gate decision to `.sprint/ci-report.yaml` (Phase 10) and carry it forward to `.sprint/merge-report.yaml` (Phase 11):

```yaml
gate_decision:
  verdict: SHIP|REVISE|BLOCKED
  timestamp: <ISO timestamp>
  rationale: |
    <1-3 sentence explanation of why this verdict was reached>

  signal_summary:
    code_review:
      pass: true|false
      unresolved_issues: <count>
      severity_max: <level>
    qa:
      pass: true|false
      tests_passing: <count>/<total>
      coverage: <percentage>
      lint_clean: true|false
      type_check_clean: true|false
      acceptance_criteria_met: <count>/<total>
    security_review:
      pass: true|false
      vulnerabilities: <count>
      severity_max: <level>
    sentinel:
      pass: true|false
      blocking_count: <count>
      total_issues: <count>
      has_report: true|false

  blockers:
    - <item preventing SHIP, if any>

  action: "Create pull request"|"Loop back to Phase 6"|"Halt sprint"
```

## Configuration

Thresholds can be adjusted per project. Defaults:

| Threshold | Default | Notes |
|-----------|---------|-------|
| Coverage minimum | 80% | REVISE if below |
| Security severity ceiling | medium | BLOCKED if high or critical |
| Max revision cycles | 2 | 3 total attempts (initial + 2 cycles), then BLOCKED |
| Lint/type check (from QA) | must pass | REVISE if dirty |

To override, add a `.sprint/config.yaml`:

```yaml
gate_thresholds:
  coverage_minimum: 70
  security_ceiling: high
  max_revision_cycles: 3
```

## Manual Override (Attended Mode)

When the sprint is running in **attended mode** (`velocity_mode: attended` in `sprint-meta.yaml`), present the gate decision to the developer and offer override options.

### Override Process

```text
1. Compute the automated verdict (SHIP / REVISE / BLOCKED) using Steps 1-3 above
2. Present the verdict and signal summary to the developer
3. Ask using AskUserQuestion:

   "Gate Decision: <VERDICT>
    Rationale: <rationale>

    What would you like to do?"

   Options:
     - "Accept verdict" → proceed with automated decision
     - "Override to SHIP" → force ship despite findings
     - "Override to REVISE" → force another implementation pass
     - "Override to BLOCKED" → halt the sprint

4. If override selected:
   - Record the override in the gate decision output
   - Use the overridden verdict for the action step
```

### Override Output

When a manual override is applied, add an `override` section to the gate decision:

```yaml
gate_decision:
  verdict: SHIP  # The overridden verdict
  automated_verdict: REVISE  # What the algorithm computed
  override:
    applied: true
    from: REVISE
    to: SHIP
    reason: |
      Developer override in attended mode.
      <developer's stated reason if provided>
    timestamp: <ISO timestamp>
  # ... rest of gate_decision fields unchanged
```

### Override Rules

- Overrides are **only available in attended mode**. In autonomous mode, the automated verdict is final.
- Overrides are **logged for audit** — the `automated_verdict` and `override` fields create a paper trail.
- Overriding to SHIP when BLOCKED still requires the developer to acknowledge the blockers.
- Override count is not tracked against `max_revision_cycles` — only automated REVISE verdicts count toward the cycle limit.

## Revision Cycle Tracking

The orchestrate command tracks cycle count in `.sprint/sprint-meta.yaml`:

```yaml
revision_cycles: 0  # Incremented each time gate returns REVISE
```

On a REVISE verdict, the orchestrate command iterates — it re-runs Phases 6-11 with prior review findings carried forward as context. Each phase overwrites its output file on the next pass.

When `revision_cycles` >= `max_revision_cycles` (default: 2):
- Escalate from `REVISE` to `BLOCKED`
- This means 3 total execution attempts (initial + 2 cycles) before halting
- Include all accumulated findings in the blocker list
- Require manual intervention

## Composition

- **Pattern:** Gate Pattern (#3 from `skills/composition-patterns/`)
- **Consumed by:** `commands/orchestrate.md` (Phase 10)
- **Reads from:** Phases 7-9 handoff files + `.sentinel/report.md` (emerging issues)
- **Writes to:** `.sprint/ci-report.yaml` (gate_decision section, Phase 10) and `.sprint/merge-report.yaml` (carried forward, Phase 11)
