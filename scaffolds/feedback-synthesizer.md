# Feedback Synthesizer

**Phase position:** Connects Phase 13 (Retrospective) back to Phase 1 (Intake)
**Priority:** Medium
**Status:** Not in development

## Purpose

Transform monitoring signals and retrospective insights into actionable intake items for the next sprint. This is what closes the loop — without it, the cycle is linear, not circular.

## Inputs

- `.sprint/monitoring-report.yaml` (Phase 12) — real signals, health assessment, actionable items
- `.sprint/retrospective.yaml` (Phase 13) — what worked, what didn't, new intake items

## Outputs

Next sprint seed file (or additions to intake queue):

```yaml
generated_intake_items:
  timestamp: <ISO timestamp>
  source_sprint: <sprint ID>

  items:
    - id: INTAKE-001
      type: bug|improvement|tech_debt|process
      title: "<short title>"
      description: |
        <detailed description>
      source: monitoring|retrospective|review_feedback
      evidence: |
        <data that triggered this item>
      priority: critical|high|medium|low
      suggested_constraints:
        - "<any known constraints>"

  process_improvements:
    - target: "<which phase or job to improve>"
      change: "<what to change>"
      rationale: "<why, based on data>"

  sprint_health_trend:
    current: healthy|warning|degraded
    previous: healthy|warning|degraded
    direction: improving|stable|declining
```

## Synthesis Rules

| Signal | Generates |
|--------|-----------|
| Coverage regression | `improvement` intake item: "Add tests for affected module" |
| Recurring review findings | `tech_debt` intake item: "Refactor pattern causing repeated issues" |
| Performance regression | `bug` intake item: "Investigate and fix performance in X" |
| Low review signal-to-noise | `process` improvement: "Adjust reviewer scope/focus" |
| New dependency vulnerabilities | `bug` intake item: "Update or replace vulnerable package" |
| Estimation inaccuracy (systematic) | `process` improvement: "Recalibrate estimation for task type X" |
| Flaky tests | `tech_debt` intake item: "Fix or quarantine flaky test" |

## Design Principles

- **Data-driven:** Every generated item traces back to a concrete signal. No vague "we should improve X."
- **Prioritized:** Items ranked by severity and impact. Critical regressions first.
- **Actionable:** Each item includes enough context to be picked up as a Sprint Phase 1 input without additional research.
- **Deduplication:** If the same signal appeared in a previous sprint's feedback and wasn't addressed, escalate its priority.

## Open Questions (Resolved)

- ~~Where does the generated intake queue live? New `.sprint/` dir for next sprint, or a shared queue?~~ → Same `.sprint/` directory as `feedback-intake.yaml`. The next sprint reads this file during Phase 1 intake.
- ~~Should high-priority items automatically start the next sprint, or wait for developer confirmation?~~ → Manual start only. When a new sprint starts, critical/high items from previous feedback are surfaced to the developer as suggestions. Never auto-triggered. See "Feedback Carry-Forward" in `commands/sprint-run.md` and Phase 1 in `skills/sprint/SKILL.md`.
- ~~How to handle the accumulation problem (more items generated than completed per sprint)?~~ → Cap at 10 items per sprint. Medium/low items expire after 2 sprints unaddressed. Only carry forward high/critical from previous sprints. See "Accumulation Safety Valve" in `skills/feedback-synthesizer/SKILL.md`.
