# Gate Decision

**Phase position:** Phase 10 (Pull Request & CI) — runs before PR creation
**Priority:** High
**Status:** Not in development

## Purpose

Automated go/no-go checkpoint. Aggregates signals from code review, QA validation, and security review to produce a ship decision. Uses the Gate composition pattern.

## Inputs

- `.sprint/review-code.yaml` (Phase 7)
- `.sprint/qa-report.yaml` (Phase 8)
- `.sprint/review-security.yaml` (Phase 9)

## Outputs

Decision: `SHIP` | `REVISE` | `BLOCKED`

```yaml
gate_decision:
  verdict: SHIP | REVISE | BLOCKED
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
  blockers:
    - <list of items preventing SHIP>

  action:
    if_ship: "Create pull request"
    if_revise: "Return to Phase 6 with findings"
    if_blocked: "Halt sprint and report"
```

## Decision Criteria

**SHIP** — All of:
- All code reviews approved (no unresolved blockers)
- No security findings above configured severity threshold
- All tests passing
- Coverage at or above threshold
- All acceptance criteria met

**REVISE** — Any of:
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
- Soft gate for REVISE items (can loop back)
- Pass-through for SHIP

## Open Questions (Resolved)

- ~~What are the default severity thresholds? (Configurable per project?)~~ → Defaults in `skills/gate-decision/SKILL.md`: coverage 80%, security ceiling medium. Configurable via `.sprint/config.yaml`.
- ~~How many revision cycles before escalating to BLOCKED?~~ → Max 2 REVISE verdicts (3 total attempts). Configurable via `max_revision_cycles`.
- ~~Should there be a manual override mechanism?~~ → Yes, in attended mode only. Developer can override verdict with audit trail. See "Manual Override" in `skills/gate-decision/SKILL.md`.
