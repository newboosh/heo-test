---
name: feedback-synthesizer
description: Synthesis rules for transforming monitoring signals and retrospective insights into actionable intake items for the next sprint. Closes the loop from Phase 13 back to Phase 1.
---

# Feedback Synthesizer Skill

**You are closing the feedback loop.** Read the monitoring report and retrospective, apply the synthesis rules below, and produce a list of concrete intake items for the next sprint. Every generated item must trace back to a specific signal.

## When to Use

This skill is consumed by `commands/sprint-run.md` during Phase 13, after the sprint-retrospective skill has run. It produces the final artifact that connects one sprint cycle to the next.

**Lifecycle context:** See `docs/SPRINT_LIFECYCLE.md`, Phase 13 → Phase 1 loop.

## Inputs

| File | Contains | Use For |
|------|----------|---------|
| `.sprint/monitoring-report.yaml` | Real signals, health assessment, actionable items | Data-driven intake items |
| `.sprint/retrospective.yaml` | What worked/didn't, review effectiveness, new intake items | Process-driven intake items |
| `.sprint/sprint-meta.yaml` | Sprint ID, timing | Source tracking |

## Synthesis Rules

Apply these rules to transform signals into intake items. Each rule maps a signal type to an intake item type.

### From Monitoring Signals

| Signal | Condition (from `measurements:` in monitoring report) | Generates |
|--------|-----------|-----------|
| Coverage regression | `measurements.coverage.delta` < 0 | `improvement`: "Add tests for <affected modules>" |
| Flaky test | `measurements.tests.flaky_tests` is non-empty | `tech_debt`: "Fix or quarantine <test name>" |
| New vulnerability | `measurements.dependencies.new_vulnerabilities` > 0 | `bug`: "Update or replace <package>" |
| Performance regression | `measurements.performance.build_time_delta` > 30% | `improvement`: "Investigate build performance" |
| Build failure | `measurements.build.status` == failure | `bug`: "Fix post-merge build failure in <area>" |
| New CI errors | `measurements.errors.new_errors_in_ci` > 0 | `bug`: "Investigate new errors: <types>" |

### From Retrospective Insights

| Insight | Condition | Generates |
|---------|-----------|-----------|
| Low review signal-to-noise | `signal_to_noise` < 0.3 for a reviewer | `process`: "Adjust <reviewer> scope or focus" |
| Estimation bias | `estimation_accuracy.bias` != balanced | `process`: "Recalibrate estimation for <task type>" |
| Recurring NEEDS_WORK loops | `needs_work_loops` > 1 | `process`: "Improve Phase 6 implementation quality" |
| Deferred tasks | `tasks_deferred` > 0 | `improvement`: "Complete deferred task: <title>" |
| Phase bottleneck | Phase N took disproportionate time | `process`: "Optimize Phase N workflow" |
| Extracted pattern | `save_as_skill` is true | `process`: "Codify pattern <name> as a skill" |

### From Previous Feedback (Deduplication)

If a previous `.sprint/feedback-intake.yaml` exists:
- Check if any items from the previous sprint were **not addressed**
- If an item appears in both previous and current feedback, **escalate its priority** one level
- Mark escalated items with `escalated: true` and `previous_sprint: <id>`

## Output

Write `.sprint/feedback-intake.yaml`:

```yaml
phase: 13
phase_name: feedback_synthesis
role: scrum_master
status: complete
timestamp: <ISO timestamp>
depends_on: retrospective

summary: |
  <1-3 sentence summary of synthesized feedback items>

synthesis:
  source_sprint: <sprint ID from sprint-meta.yaml>
  synthesis_version: "1.0"

  items:
    - id: INTAKE-001
      type: bug|improvement|tech_debt|process
      title: "<short actionable title>"
      description: |
        <detailed description with enough context to start work>
      source: monitoring|retrospective|review_feedback
      evidence: |
        <specific data point that triggered this item>
      priority: critical|high|medium|low
      escalated: false
      suggested_constraints:
        - "<known constraint if any>"

  process_improvements:
    - target: "<phase name or job to improve>"
      change: "<what to change>"
      rationale: "<why, citing data>"

  sprint_health_trend:
    current: <from monitoring health_assessment.overall>
    previous: <from previous sprint's feedback if exists, else "unknown">
    direction: improving|stable|declining|unknown

outputs:
  - .sprint/feedback-intake.yaml

open_issues: []

signals:
  pass: true
  confidence: <high/medium>
  blockers: []
```

## Priority Rules

Assign priority based on impact and urgency:

| Priority | Criteria |
|----------|----------|
| `critical` | Build broken, security vulnerability (high/critical), tests failing |
| `high` | Coverage regression > 5%, recurring unfixed issues, escalated items |
| `medium` | Coverage regression 1-5%, new tech debt, estimation drift |
| `low` | Process tweaks, minor optimizations, reviewer tuning |

Items are ordered by priority (critical first), then by source (monitoring before retrospective — real signals take precedence).

## Design Principles

- **Data-driven.** Every item traces to a specific signal or metric. If you can't point to data, don't generate the item.
- **Actionable.** Each item includes enough context to be picked up as a Phase 1 input without additional research. Include file paths, module names, and specific numbers.
- **Deduplicated.** Don't generate items for problems that were already fixed during the sprint. Cross-reference monitoring signals with what was addressed in the NEEDS_WORK loops.
- **Bounded.** Cap generated items at 10 per sprint. If more than 10, keep only the highest priority items. Accumulation kills velocity.

## Accumulation Safety Valve

If the feedback queue is growing faster than items are addressed:
- Flag this as a `process` improvement: "Feedback queue growing — consider dedicated tech debt sprint"
- Only carry forward items of `high` or `critical` priority from previous sprints
- Let `medium` and `low` items expire after 2 sprints unaddressed

## Composition

- **Pattern:** Pipeline (reads retrospective → produces intake)
- **Consumed by:** `commands/sprint-run.md` (Phase 13b)
- **Feeds into:** Phase 1 of the next sprint cycle
- **Reads from:** `.sprint/monitoring-report.yaml`, `.sprint/retrospective.yaml`
- **Writes to:** `.sprint/feedback-intake.yaml`
