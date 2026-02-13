# Sprint Retrospective Runner

**Phase position:** Phase 13 (Retrospective)
**Priority:** Medium
**Status:** Not in development

## Purpose

Analyze the completed sprint and generate improvement items. Combines monitoring signals (Phase 12) with sprint execution data (Phases 1-11) to produce a retrospective that feeds back into the next sprint's intake.

Absorbs concepts from the retired `commands/learn.md` (pattern extraction, session learning).

## Inputs

- All `.sprint/*.yaml` files from the completed sprint
- `.sprint/monitoring-report.yaml` (Phase 12) — real signals
- `.sprint/execution-log.md` (Phase 6) — implementation notes
- `.sprint/sprint-meta.yaml` — sprint timing and metadata

## Outputs

`.sprint/retrospective.yaml`:

```yaml
phase: 13
phase_name: retrospective
role: scrum_master
status: complete
timestamp: <ISO timestamp>
depends_on: monitoring

sprint_summary:
  started: <timestamp>
  completed: <timestamp>
  duration_hours: <number>
  tasks_planned: <count>
  tasks_completed: <count>
  tasks_deferred: <count>

what_worked:
  - observation: "<something that went well>"
    evidence: "<data supporting this>"
    recommendation: keep

what_didnt_work:
  - observation: "<something that went poorly>"
    evidence: "<data supporting this>"
    recommendation: change|stop
    suggested_improvement: "<concrete action>"

phase_analysis:
  - phase: 1
    phase_name: intake
    issues: <count>
    notes: "<any observations>"
  # ... for each phase

review_effectiveness:
  - reviewer: code-reviewer
    issues_found: <count>
    issues_that_mattered: <count>
    signal_to_noise: <ratio>
  - reviewer: security-reviewer
    issues_found: <count>
    issues_that_mattered: <count>
    signal_to_noise: <ratio>

estimation_accuracy:
  planned_vs_actual:
    - task_id: TASK-001
      estimated: S
      actual_effort: M
  overall_accuracy: <percentage>

patterns_extracted:
  - name: "<pattern name>"
    context: "<when this applies>"
    description: "<the pattern>"
    save_as_skill: true|false

new_intake_items:
  - type: improvement
    description: "Coverage regression in module X needs test backfill"
    source: monitoring_signals
    priority: high
  - type: process
    description: "Security review caught 0 issues — consider reducing scope"
    source: review_effectiveness
    priority: low
```

## Analysis Dimensions

1. **Phase timing:** Which phases took longest? Where are bottlenecks?
2. **Review effectiveness:** Which reviewers found real issues vs noise?
3. **Estimation accuracy:** Were backlog estimates close to actual?
4. **Pattern extraction:** What reusable patterns emerged? (from retired `learn.md`)
5. **Monitoring signals:** What did post-merge data reveal?
6. **Process friction:** Where did the pipeline stall or loop?

## Relationship to Existing Assets

| Existing Asset | Relationship |
|---------------|-------------|
| `skills/continuous-learning/` | Feeds into pattern extraction |
| `commands/learn.md` (retired) | Pattern extraction concept absorbed here |
| Feedback Synthesizer | Consumes this output to generate next sprint intake |

## Open Questions (Resolved)

- ~~How much historical data should it reference? (Just this sprint, or compare to previous sprints?)~~ → Primary: this sprint's data. Cross-sprint trends via monitoring report's lookback window. First sprint establishes baselines.
- ~~Should extracted patterns automatically become skill files in `.claude/skills/learned/`?~~ → No auto-creation. Patterns flagged with `save_as_skill: true` are presented to the developer for confirmation. In attended mode, skill-creator is invoked if approved. In autonomous mode, skill extraction is skipped. See "Skill Extraction" in `skills/sprint-retrospective/SKILL.md`.
- ~~How to handle the first sprint (no baseline for comparison)?~~ → Skip trend comparisons, set baselines, note "first sprint" in summary. See "First Sprint Handling" in the retrospective skill.
