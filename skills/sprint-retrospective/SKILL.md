---
name: sprint-retrospective
description: Analysis methodology for completed sprints. Read all sprint phase handoffs, evaluate what worked, what didn't, review effectiveness, estimation accuracy, and extract reusable patterns. Used by the Sprint Runner at Phase 13.
---

# Sprint Retrospective Skill

**You are analyzing a completed sprint.** Read all `.sprint/*.yaml` handoff files and produce a data-driven retrospective. Every observation must cite evidence from the sprint artifacts. No subjective filler.

## When to Use

This skill is consumed by `commands/sprint-run.md` during Phase 13. It runs after `commands/collect-signals.md` (Phase 12) has written `.sprint/monitoring-report.yaml`.

**Lifecycle context:** See `docs/SPRINT_LIFECYCLE.md`, Phase 13.

## Inputs

Read all files from `.sprint/`:

| File | Contains | Use For |
|------|----------|---------|
| `sprint-meta.yaml` | Sprint timing, velocity mode | Duration, loop counts |
| `input.yaml` | Original requirements | Compare to what was delivered |
| `product.yaml` | User stories, acceptance criteria | Scope creep detection |
| `backlog.yaml` | Planned tasks with estimates | Estimation accuracy |
| `execution-log.md` | Implementation progress | Task completion, blockers |
| `review-code.yaml` | Code review findings | Review effectiveness |
| `review-security.yaml` | Security findings | Security review value |
| `qa-report.yaml` | Test results, coverage | Quality metrics |
| `ci-report.yaml` | Build/lint/type results | CI health |
| `merge-report.yaml` | Merge status, gate decision | Ship decision accuracy |
| `monitoring-report.yaml` | Post-merge signals | Real-world impact |

## Analysis Framework

### Dimension 1: Sprint Summary

Compare planned vs actual:

```yaml
sprint_summary:
  started: <from sprint-meta.yaml>
  completed: <current timestamp>
  duration_hours: <calculated>
  velocity_mode: <from sprint-meta.yaml>
  tasks_planned: <count from backlog.yaml>
  tasks_completed: <count from execution-log.md completed tasks>
  tasks_deferred: <planned minus completed>
  needs_work_loops: <from sprint-meta.yaml if tracked>
```

### Dimension 2: What Worked

Look for evidence of success:

- **All tests passing** after implementation → TDD process worked
- **No security findings** at gate → security review caught issues early or code was clean
- **Coverage improved** → test writing discipline
- **Gate decision was SHIP on first pass** → planning was thorough
- **No NEEDS_WORK loops** → reviews and implementation aligned

Each observation needs:
```yaml
what_worked:
  - observation: "<what went well>"
    evidence: "<specific data from sprint files>"
    recommendation: keep
```

### Dimension 3: What Didn't Work

Look for evidence of problems:

- **NEEDS_WORK loops** → review findings not addressed in implementation
- **Coverage declined** → tests not matching new code
- **Tasks deferred** → scope was too large or estimates too small
- **Build failures in CI** → local testing didn't catch issues
- **Security findings at gate** → security concerns introduced during implementation
- **Flaky tests** in monitoring → test quality issues

Each observation needs:
```yaml
what_didnt_work:
  - observation: "<what went poorly>"
    evidence: "<specific data from sprint files>"
    recommendation: change|stop
    suggested_improvement: "<concrete action to take>"
```

### Dimension 4: Phase-by-Phase Analysis

For each of the 13 phases, note:
- Did it produce a valid handoff file?
- Were there any issues flagged by downstream phases?
- Any observations about quality or completeness?

```yaml
phase_analysis:
  - phase: 1
    phase_name: intake
    handoff_exists: true|false
    issues_flagged_downstream: <count>
    notes: "<observations>"
  # ... repeat for all 13 phases
```

### Dimension 5: Review Effectiveness

Compare what each reviewer found vs what actually mattered post-merge:

```yaml
review_effectiveness:
  - reviewer: code-reviewer
    issues_found: <count from review-code.yaml>
    issues_that_mattered: <count of issues that correspond to real problems in monitoring>
    signal_to_noise: <ratio>
  - reviewer: security-reviewer
    issues_found: <count from review-security.yaml>
    issues_that_mattered: <count>
    signal_to_noise: <ratio>
  - reviewer: qa-agent
    issues_found: <count from qa-report.yaml>
    issues_that_mattered: <count>
    signal_to_noise: <ratio>
```

**How to determine "mattered":** Cross-reference review findings with monitoring report. If monitoring shows a problem in an area a reviewer flagged, it mattered. If monitoring is clean in areas flagged, it was noise (or the fix worked — note which).

### Dimension 6: Estimation Accuracy

Compare backlog estimates to actual effort:

```yaml
estimation_accuracy:
  planned_vs_actual:
    - task_id: TASK-001
      title: "<task title>"
      estimated: XS|S|M|L|XL
      actual_effort: XS|S|M|L|XL  # Inferred from execution log timestamps and complexity
  overall_accuracy: <percentage of tasks where estimate matched>
  bias: underestimate|overestimate|balanced
```

**Inferring actual effort:** Use execution log timestamps. If a task estimated as S took significantly longer than other S tasks, mark it as M or L.

### Dimension 7: Pattern Extraction

Identify reusable patterns that emerged during the sprint (absorbed from retired `learn.md`):

```yaml
patterns_extracted:
  - name: "<descriptive pattern name>"
    context: "<when this applies>"
    description: "<the pattern or technique>"
    save_as_skill: true|false
```

Look for:
- Error resolution patterns that could apply to future sprints
- Debugging techniques that were non-obvious
- Architecture decisions that proved effective
- Workarounds for tool or library quirks

Only extract patterns that are genuinely reusable. Don't extract trivial fixes.

### Dimension 8: New Intake Items

Generate items for the next sprint based on evidence:

```yaml
new_intake_items:
  - type: improvement|bug|tech_debt|process
    description: "<what needs to happen>"
    source: monitoring_signals|review_effectiveness|estimation_analysis|phase_analysis
    priority: critical|high|medium|low
    evidence: "<data supporting this>"
```

## Output

Write `.sprint/retrospective.yaml` with the standard handoff fields plus all dimensions above:

```yaml
phase: 13
phase_name: retrospective
role: scrum_master
status: complete
timestamp: <ISO timestamp>
depends_on: monitoring

summary: |
  <2-3 sentence summary of the sprint retrospective>

sprint_summary:
  # ... Dimension 1

what_worked:
  # ... Dimension 2

what_didnt_work:
  # ... Dimension 3

phase_analysis:
  # ... Dimension 4

review_effectiveness:
  # ... Dimension 5

estimation_accuracy:
  # ... Dimension 6

patterns_extracted:
  # ... Dimension 7

new_intake_items:
  # ... Dimension 8

outputs:
  - .sprint/retrospective.yaml

open_issues: []

signals:
  pass: true
  confidence: high|medium
  blockers: []
```

## Skill Extraction

When patterns are extracted with `save_as_skill: true`, the Sprint Runner handles the actual skill creation after the retrospective completes.

### What to Flag for Extraction

Only flag a pattern for skill extraction if **all** of these are true:
- The pattern is genuinely reusable (applies beyond this specific sprint)
- The pattern is non-trivial (not a one-liner or obvious fix)
- The pattern can be expressed as a self-contained skill (clear inputs → outputs)

### Pattern Output Format

For patterns flagged with `save_as_skill: true`, include enough detail for the skill-creator to work with:

```yaml
patterns_extracted:
  - name: "retry-with-backoff"
    context: "When calling external APIs that may rate-limit"
    description: |
      Implement exponential backoff with jitter for API calls.
      Start at 1s, double each retry, add random jitter of 0-500ms.
      Max 3 retries before failing.
    save_as_skill: true
    skill_metadata:
      suggested_name: "retry-pattern"
      category: "backend-patterns"
      triggers: ["API call", "rate limit", "retry"]
```

The `skill_metadata` field is only required when `save_as_skill: true`. It provides the Sprint Runner with enough context to prompt the developer and invoke the skill-creator.

## First Sprint Handling

If this is the first sprint (no previous retrospective data):
- Skip trend comparisons
- Set baselines for future comparison
- Note "first sprint — establishing baselines" in summary

## Composition

- **Pattern:** Pipeline (reads monitoring → produces retrospective)
- **Consumed by:** `commands/sprint-run.md` (Phase 13)
- **Feeds into:** `skills/feedback-synthesizer/` (same phase, runs after)
- **Related:** `skills/continuous-learning/` (complementary pattern extraction)
