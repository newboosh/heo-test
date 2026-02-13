# Orchestrate Command

Execute Phases 6-11 of the sprint lifecycle: implementation through merge. Reads the backlog, sequences agents, writes validated handoff files, and manages the NEEDS_WORK loop.

**Lifecycle context:** `docs/SPRINT_LIFECYCLE.md` | **Handoff protocol:** `skills/composition-patterns/`

## Usage

```text
/orchestrate sprint
```

## State Management

After each phase completes, update `.sprint/sprint-meta.yaml`:

1. Set `current_phase` to the next phase number
2. Append to `phase_log`:

```yaml
- phase: 7
  phase_name: code_review
  status: complete
  started_at: "<ISO timestamp>"
  completed_at: "<ISO timestamp>"
  output_file: review-code.yaml
  validated: true
```

If a phase fails, set `status: failed` in the log entry and `last_error` in the metadata.

3. Track NEEDS_WORK loop count:

```yaml
needs_work_loops: 0  # Increment each time verdict is NEEDS_WORK (max 2)
```

## Sprint Workflow

Read `.sprint/backlog.yaml` for the task list, then execute phases in order:

| Phase | Invoke | Output | Template |
|-------|--------|--------|----------|
| 6. Implementation | `agents/tdd-guide.md` per task | `execution-status.yaml`, `execution-log.md` | `skills/sprint/templates/execution-status.yaml` (log is markdown, no envelope) |
| 7. Code Review | `agents/code-reviewer.md` + `agents/qa-agent.md` | `review-code.yaml` | `skills/sprint/templates/review-code.yaml` |
| 8. Security Review | `agents/security-reviewer.md` | `review-security.yaml` | `skills/sprint/templates/review-security.yaml` |
| 9. QA Validation | `agents/qa-agent.md` + `skills/verification-loop/` + `agents/e2e-runner.md` | `qa-report.yaml` | `skills/sprint/templates/qa-report.yaml` |
| 10. CI/CD | `commands/ci.md` + `commands/verify.md` | `ci-report.yaml` | `skills/sprint/templates/ci-report.yaml` |
| 11. Merge | `skills/gate-decision/` then `commands/push.md` | `merge-report.yaml` | `skills/sprint/templates/merge-report.yaml` |

### Envelope & Validation

Every YAML output includes the standard handoff envelope (`phase`, `phase_name`, `role`, `status`, `timestamp`, `depends_on`, `signals`, `_schema_version`) plus phase-specific body fields defined in the template.

After writing each `.sprint/*.yaml`, validate:

```bash
python3 -m scripts.sprint.validate .sprint/
```

Do NOT proceed to the next phase until validation passes.

### Parallel Execution

Phases 7 (code_review) and 8 (security_review) run sequentially: Phase 8 depends on Phase 7 completing. Phase 9 (qa) depends on Phase 8 (security_review) completing.

### NEEDS_WORK Loop

At Phase 11, apply `skills/gate-decision/` to aggregate signals from Phases 7-10. See the NEEDS_WORK Loop Outcomes section below for verdict handling.

## Sprint Workflow Detail

When invoked as `/orchestrate sprint`:

**Every YAML phase output MUST include the standard handoff envelope** (phase, phase_name, role, status, timestamp, depends_on, signals, etc.) plus phase-specific body fields. Templates in `skills/sprint/templates/` define the schema for each phase. Validate with `python3 -m scripts.sprint.validate .sprint/`. Markdown outputs (e.g., `execution-log.md`) do not require the envelope.

### Phase 6: Implementation (TDD)
- Read `.sprint/backlog.yaml` for ordered tasks
- Invoke `tdd-guide` agent for each task
- Write `.sprint/execution-log.md` with detailed progress
- Write `.sprint/execution-status.yaml` with structured handoff
- **Output:** `.sprint/execution-status.yaml`, `.sprint/execution-log.md`

```yaml
# .sprint/execution-status.yaml
phase: 6
phase_name: implementation
role: developer
status: complete | failed | blocked
timestamp: <ISO timestamp>
depends_on: backlog

summary: |
  <1-3 sentence summary of implementation results>

tasks_completed:
  - task_id: TASK-001
    title: "<title>"
    status: complete | failed | skipped
    tests_written: <count>
    tests_passing: <count>
    files_changed:
      - "<path>"

tasks_remaining: []

execution_stats:
  total_tasks: <count>
  completed: <count>
  failed: <count>
  skipped: <count>

outputs:
  - .sprint/execution-status.yaml
  - .sprint/execution-log.md

open_issues:
  - <unresolved items>

signals:
  pass: <true if all tasks completed>
  confidence: <high/medium/low>
  blockers: []
```

### Phase 7: Code Review
- Invoke multiple reviewers (multiple flavors intentional):
  - `code-reviewer` agent — style/quality
  - `qa-agent` — compliance/completeness (distinct perspective)
  - CodeRabbit integration (if configured)
- Run reviewers in parallel where possible
- **Output:** `.sprint/review-code.yaml`
- **Required body:** `findings` (list) — see `skills/sprint/templates/review-code.yaml`

```yaml
# .sprint/review-code.yaml
phase: 7
phase_name: code_review
role: senior_developer
status: complete
timestamp: <ISO timestamp>
depends_on: implementation

summary: |
  <1-3 sentence summary of code review findings>

reviews:
  - reviewer: code-reviewer
    approval: approved | changes_requested | commented
    findings:
      - severity: info | warning | error | critical
        file: "<path>"
        description: "<finding>"
  - reviewer: qa-agent
    approval: approved | changes_requested
    findings: []
  - reviewer: coderabbit
    approval: approved | changes_requested
    findings: []

aggregate:
  approved: <true if all reviewers approved>
  total_findings: <count>
  critical_findings: <count>
  unresolved: <count>

outputs:
  - .sprint/review-code.yaml

open_issues:
  - <unresolved review comments>

signals:
  pass: <true if all approved>
  confidence: <high/medium/low>
  blockers: []
```

### Phase 8: Security Review
- Invoke `security-reviewer` agent
- **Output:** `.sprint/review-security.yaml`
- **Required body:** `findings` (list) — see `skills/sprint/templates/review-security.yaml`

```yaml
# .sprint/review-security.yaml
phase: 8
phase_name: security_review
role: security_engineer
status: complete
timestamp: <ISO timestamp>
depends_on: code_review

summary: |
  <1-3 sentence summary of security review>

vulnerabilities:
  - id: VULN-001
    severity: none | low | medium | high | critical
    category: "<e.g., injection, XSS, auth bypass>"
    file: "<path>"
    description: "<finding>"
    remediation: "<suggested fix>"

aggregate:
  total_vulnerabilities: <count>
  severity_max: none | low | medium | high | critical
  pass: <true if no findings above threshold>

outputs:
  - .sprint/review-security.yaml

open_issues:
  - <unresolved security concerns>

signals:
  pass: <true if severity_max below threshold>
  confidence: <high/medium/low>
  blockers: []
```

### Phase 9: QA Validation
- Invoke `qa-agent` for acceptance criteria verification
- Run `verification-loop` skill (type check → lint → format → tests → coverage)
- Run `e2e-runner` agent if applicable
- **Output:** `.sprint/qa-report.yaml`
- **Required body:** `test_results` (mapping) — see `skills/sprint/templates/qa-report.yaml`

```yaml
# .sprint/qa-report.yaml
phase: 9
phase_name: qa
role: qa_engineer
status: complete
timestamp: <ISO timestamp>
depends_on: security_review

summary: |
  <1-3 sentence summary of QA results>

test_results:
  total: <count>
  passing: <count>
  failing: <count>
  skipped: <count>

coverage:
  percentage: <number>
  threshold: <number>
  meets_threshold: <true/false>

acceptance_criteria:
  met: <count>
  total: <count>
  unmet:
    - story_ref: US-001
      criterion: "<unmet criterion>"

verification_loop:
  type_check: pass | fail
  lint: pass | fail
  format: pass | fail
  tests: pass | fail
  coverage: pass | fail

outputs:
  - .sprint/qa-report.yaml

open_issues:
  - <unresolved QA items>

signals:
  pass: <true if all criteria met and tests pass>
  confidence: <high/medium/low>
  blockers: []
```

### Phase 10: CI/CD Pipeline
- Run `ci` command (build, test suite, lint, type check)
- Run `verify` command
- **Output:** `.sprint/ci-report.yaml`
- **Required body:** `pipeline` (mapping) — see `skills/sprint/templates/ci-report.yaml`

```yaml
# .sprint/ci-report.yaml
phase: 10
phase_name: ci_cd
role: devops_engineer
status: complete
timestamp: <ISO timestamp>
depends_on: qa

summary: |
  <1-3 sentence summary of CI/CD results>

build:
  status: success | failure
  duration_seconds: <number>
  workflow_name: "<name>"

lint:
  clean: <true/false>
  issues: <count>

type_check:
  clean: <true/false>
  errors: <count>

test_suite:
  status: pass | fail
  total: <count>
  passing: <count>
  failing: <count>

outputs:
  - .sprint/ci-report.yaml

open_issues:
  - <CI issues>

signals:
  pass: <true if build green, lint clean, types clean>
  confidence: <high/medium/low>
  blockers: []
```

### Phase 11: Merge & Deploy
- Apply `skills/gate-decision/` to aggregate signals from Phases 7-10
- If `SHIP`: invoke `push` command → PR creation → merge
- If `NEEDS_WORK`: loop back to Phase 6 with review findings (max 2 loops, tracked in `sprint-meta.yaml`)
- If `BLOCKED`: halt with report
- **Output:** `.sprint/merge-report.yaml` (includes gate_decision section)
- **Required body:** `gate_decision` with `verdict` (SHIP/NEEDS_WORK/BLOCKED) — see `skills/sprint/templates/merge-report.yaml`

```yaml
# .sprint/merge-report.yaml
phase: 11
phase_name: merge
role: release_manager
status: complete
timestamp: <ISO timestamp>
depends_on: ci_cd

summary: |
  <1-3 sentence summary of merge result>

gate_decision:
  verdict: SHIP | NEEDS_WORK | BLOCKED
  timestamp: <ISO timestamp>
  rationale: |
    <explanation>
  signal_summary:
    code_review: { pass: <bool>, unresolved_issues: <count> }
    security_review: { pass: <bool>, vulnerabilities: <count> }
    qa: { pass: <bool>, coverage: <pct> }
    ci_cd: { pass: <bool>, build_status: <status> }
  blockers: []
  action: "<action taken>"

merge:
  pr_number: <number>
  pr_url: "<url>"
  merge_commit: "<sha>"
  target_branch: "<branch>"
  release_notes: |
    <summary of changes>

outputs:
  - .sprint/merge-report.yaml

open_issues: []

signals:
  pass: <true if SHIP verdict and merge succeeded>
  confidence: <high/medium/low>
  blockers: []
```

## NEEDS_WORK Loop Outcomes

- **SHIP**: invoke `commands/push.md` for PR creation and merge
- **NEEDS_WORK**: loop back to Phase 6 with review findings attached. Maximum 2 loops (3 total attempts). Track `needs_work_loops` in `sprint-meta.yaml`.
- **BLOCKED**: halt. Record in `sprint-meta.yaml` with `status: blocked` and `last_error`.

If a 3rd attempt still results in NEEDS_WORK (i.e., `needs_work_loops` reaches 2), escalate to BLOCKED.

## Error Handling

### Validation Failure

If `python3 -m scripts.sprint.validate` fails after a phase:

1. Read error output — identifies the schema violation (missing field, wrong type)
2. Fix the output file to match the template
3. Re-run validation
4. Do not advance until validation passes

### Agent Failure

If an agent times out or produces no output:

1. Retry the phase once
2. If retry fails, set `status: failed` in phase_log and `last_error` in sprint-meta.yaml
3. Halt with a partial report in `.sprint/merge-report.yaml` (verdict: BLOCKED) explaining which phases succeeded and which failed

### NEEDS_WORK Exhaustion

After 3 total attempts (initial + 2 NEEDS_WORK loops):

1. Set `status: blocked` in sprint-meta.yaml
2. Write `merge-report.yaml` with `verdict: BLOCKED` and accumulated findings
3. Suggest manual intervention steps based on review findings

## Arguments

$ARGUMENTS:
- `sprint` — Execute Phases 6-11, reading tasks from `.sprint/backlog.yaml`

## Composition

**Invokes:**
- `agents/tdd-guide.md` — Phase 6 implementation
- `agents/code-reviewer.md` — Phase 7 code quality review
- `agents/qa-agent.md` — Phase 7 compliance review, Phase 9 acceptance verification
- `agents/security-reviewer.md` — Phase 8 vulnerability assessment
- `agents/e2e-runner.md` — Phase 9 end-to-end tests (if applicable)
- `skills/verification-loop/` — Phase 9 multi-check verification
- `commands/ci.md` — Phase 10 build/test/lint pipeline
- `commands/verify.md` — Phase 10 comprehensive verification
- `skills/gate-decision/` — Phase 11 ship/no-ship decision
- `commands/push.md` — Phase 11 PR creation and merge

**Reads from the following artefacts:**
- `.sprint/backlog.yaml` — ordered task list from Phase 5
- `.sprint/sprint-meta.yaml` — current phase, needs_work_loops, retry state

**Writes to the following artefacts:**
- `.sprint/execution-log.md` — Phase 6
- `.sprint/execution-status.yaml` — Phase 6
- `.sprint/review-code.yaml` — Phase 7
- `.sprint/review-security.yaml` — Phase 8
- `.sprint/qa-report.yaml` — Phase 9
- `.sprint/ci-report.yaml` — Phase 10
- `.sprint/merge-report.yaml` — Phase 11
- `.sprint/sprint-meta.yaml` — updated after each phase (current_phase, phase_log)

## Used By

Called by `commands/sprint-run.md` after Phase 5 (Backlog) completes.

Standalone workflows (feature, bugfix, refactor, security) were previously documented here. For ad-hoc agent sequencing outside the sprint lifecycle, see `skills/composition-patterns/` (pipeline and delegation patterns).
