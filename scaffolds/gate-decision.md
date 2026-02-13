# Gate Decision

**Phase position:** Between Phase 10 (CI/CD) and Phase 11 (Merge)
**Priority:** High
**Status:** Not in development

## Purpose

Automated go/no-go checkpoint. Aggregates signals from code review, security review, QA, and CI to produce a ship decision. Uses the Gate composition pattern.

## Inputs

- `.sprint/review-code.yaml` (Phase 7)
- `.sprint/review-security.yaml` (Phase 8)
- `.sprint/qa-report.yaml` (Phase 9)
- `.sprint/ci-report.yaml` (Phase 10)

## Outputs

Decision: `SHIP` | `NEEDS WORK` | `BLOCKED`

```yaml
gate_decision:
  verdict: SHIP | NEEDS_WORK | BLOCKED
  timestamp: <ISO timestamp>
  rationale: |
    <Why this decision was made>

  signal_summary:
    code_review:
      pass: true|false
      unresolved_issues: <count>
      severity_max: info|warning|error|critical
    security_review:
      pass: true|false
      vulnerabilities: <count>
      severity_max: none|low|medium|high|critical
    qa:
      pass: true|false
      tests_passing: <count>/<total>
      coverage: <percentage>
      acceptance_criteria_met: <count>/<total>
    ci:
      pass: true|false
      build_status: success|failure
      lint_clean: true|false
      type_check_clean: true|false

  blockers:
    - <list of items preventing SHIP>

  action:
    if_ship: "Proceed to Phase 11 (Merge)"
    if_needs_work: "Return to Phase 6 with findings"
    if_blocked: "Halt sprint and report"
```

## Decision Criteria

**SHIP** — All of:
- All code reviews approved (no unresolved blockers)
- No security findings above configured severity threshold
- All tests passing
- Coverage at or above threshold
- CI pipeline green
- All acceptance criteria met

**NEEDS WORK** — Any of:
- Unresolved review comments (non-blocking severity)
- Coverage below threshold but tests passing
- Minor security findings below threshold

**BLOCKED** — Any of:
- Critical security vulnerability
- Build failure
- Test failures in critical paths
- Unresolvable review conflicts

## Composition Pattern

This is a **Gate Pattern** (Pattern #3 from composition-patterns):
- Hard gate for BLOCKED items
- Soft gate for NEEDS WORK items (can loop back)
- Pass-through for SHIP

## Open Questions (Resolved)

- ~~What are the default severity thresholds? (Configurable per project?)~~ → Defaults in `skills/gate-decision/SKILL.md`: coverage 80%, security ceiling medium. Configurable via `.sprint/config.yaml`.
- ~~How many NEEDS WORK loops before escalating to BLOCKED?~~ → Max 2 NEEDS_WORK verdicts (3 total attempts). Configurable via `max_needs_work_verdicts`.
- ~~Should there be a manual override mechanism?~~ → Yes, in attended mode only. Developer can override verdict with audit trail. See "Manual Override" in `skills/gate-decision/SKILL.md`.
