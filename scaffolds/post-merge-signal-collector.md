# Post-Merge Signal Collector

**Phase position:** Phase 12 (Monitoring)
**Priority:** High
**Status:** Not in development

## Purpose

Gather real signals after merge. This is the highest-priority gap in the lifecycle. The entire feedback loop depends on having concrete data about what happened after code hit the target branch.

## Inputs

- `.sprint/merge-report.yaml` (Phase 11) — PR URL, merge commit, target branch
- Access to CI/CD system outputs (GitHub Actions, test results)
- Access to git history (coverage reports, test history)

## Outputs

`.sprint/monitoring-report.yaml`:

```yaml
phase: 12
phase_name: monitoring
role: sre
status: complete
timestamp: <ISO timestamp>
depends_on: merge_deploy

signals:
  build:
    status: success|failure
    duration_seconds: <number>
    compared_to_average: faster|normal|slower

  tests:
    total: <count>
    passing: <count>
    failing: <count>
    skipped: <count>
    new_tests_added: <count>
    flaky_tests: []

  coverage:
    current: <percentage>
    previous: <percentage>
    delta: <+/- percentage>
    trend: improving|stable|declining
    uncovered_critical_paths: []

  errors:
    new_errors_in_ci: <count>
    error_types: []

  performance:
    build_time_delta: <seconds>
    test_time_delta: <seconds>

  dependencies:
    new_vulnerabilities: <count>
    outdated_packages: <count>

health_assessment:
  overall: healthy|warning|degraded
  concerns:
    - <list of items that need attention>
  improvements:
    - <list of positive trends>

actionable_items:
  - type: coverage_regression
    description: "Coverage dropped 2% in module X"
    suggested_action: "Add tests for functions Y, Z"
  - type: flaky_test
    description: "test_foo intermittently fails"
    suggested_action: "Investigate race condition"
```

## Signal Sources

| Signal | Source | Method |
|--------|--------|--------|
| Build status | GitHub Actions | `gh run list`, `gh run view` |
| Test results | pytest/jest output | Parse CI artifacts |
| Coverage | coverage.py / istanbul | Compare before/after reports |
| Error rates | CI logs | Parse for new errors |
| Dependencies | pip-audit / npm audit | Run vulnerability scan |
| Performance | Build/test timing | Compare to rolling average |

## Key Design Decisions

- **Real signals only.** No subjective assessments. Every item in the report must come from a measurable, reproducible source.
- **Deltas over absolutes.** Show what changed relative to previous state, not just current state. "Coverage went from 82% to 80%" is more actionable than "Coverage is 80%."
- **Actionable items.** Every concern should have a suggested action. Don't just report problems — propose solutions.

## Open Questions (Resolved)

- ~~What CI systems do we need to integrate with? (GitHub Actions assumed as primary)~~ → GitHub Actions via `gh` CLI. Other CI systems not supported yet.
- ~~How far back should trend analysis look? (Last 5 merges? Last sprint?)~~ → Default: last 5 workflow runs. Configurable via `.sprint/config.yaml` (`trend_lookback_runs` or `trend_lookback_days`). See "Trend Lookback Window" in `commands/collect-signals.md`.
- ~~Should this run as a post-merge hook or be explicitly invoked by the Sprint Runner?~~ → Explicitly invoked by Sprint Runner via `/collect-signals`.
- ~~Where do coverage reports and test artifacts live? (Varies per project)~~ → Primary source: `.sprint/qa-report.yaml` from Phase 9. Fallback: run `pytest --cov` locally.
