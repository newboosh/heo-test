# Collect Signals

Gather real post-merge signals from CI/CD systems, test history, and dependency audits. Writes `.sprint/monitoring-report.yaml` with measurable data only — no subjective assessments.

**Lifecycle context:** Phase 12 in `docs/SPRINT_LIFECYCLE.md`

## Usage

```
/collect-signals
```

No arguments. Reads `.sprint/merge-report.yaml` for PR/commit context.

## Instructions

**You are collecting real signals after a merge.** Run the commands below, parse their output, and assemble a structured monitoring report. Every data point must come from a measurable, reproducible source.

### 1. Read Merge Context

Read `.sprint/merge-report.yaml` to get:
- PR number / URL
- Merge commit SHA
- Target branch
- Timestamp of merge

If the file doesn't exist, warn and collect what signals are available without PR-specific data.

### 2. Collect Build Signals

```bash
# Get the latest workflow runs for this branch
gh run list --branch <target-branch> --limit 5 --json status,conclusion,name,createdAt,updatedAt

# Get details of the most recent run
gh run view <run-id> --json status,conclusion,jobs
```

Extract:
- `build.status`: success or failure
- `build.duration_seconds`: time from start to finish
- `build.workflow_name`: which CI workflow ran

### 3. Collect Test Signals

```bash
# Run tests locally to get fresh results
pytest --tb=short -q 2>&1 | tail -20

# If coverage reporting is configured
pytest --cov --cov-report=term-missing -q 2>&1 | tail -30
```

Extract:
- `tests.total`, `tests.passing`, `tests.failing`, `tests.skipped`
- `tests.new_tests_added`: compare test count to previous sprint (if `.sprint/` history available)

For flaky test detection:
```bash
# Check if any tests have inconsistent results in CI
gh run view <run-id> --json jobs --jq '.jobs[].steps[] | select(.conclusion == "failure") | .name'
```

### 4. Collect Coverage Signals

```bash
# Current coverage
pytest --cov --cov-report=term 2>&1 | grep "TOTAL"

# If a previous coverage report exists
# Compare .sprint/qa-report.yaml coverage field to current
```

Extract:
- `coverage.current`: current percentage
- `coverage.previous`: from `.sprint/qa-report.yaml` if available
- `coverage.delta`: difference
- `coverage.trend`: improving / stable / declining

### 5. Collect Dependency Signals

```bash
# Python projects
pip-audit 2>&1 | tail -20

# Or with safety
safety check 2>&1 | tail -20

# Node projects
npm audit --json 2>&1 | head -50
```

Extract:
- `dependencies.new_vulnerabilities`: count
- `dependencies.outdated_packages`: count

If neither tool is available, skip this section and note it as unavailable.

### 6. Collect Error Signals

```bash
# Check CI logs for errors in recent runs
gh run view <run-id> --log-failed 2>&1 | tail -30
```

Extract:
- `errors.new_errors_in_ci`: count of distinct error types
- `errors.error_types`: list of error categories

### 7. Collect Performance Signals

```bash
# Build time from CI
gh run view <run-id> --json createdAt,updatedAt --jq '{start: .createdAt, end: .updatedAt}'

# Test execution time
pytest --tb=no -q 2>&1 | grep "passed" | head -1
```

Extract:
- `performance.build_time_delta`: compared to rolling average (if history available)
- `performance.test_time_delta`: compared to previous run

### 8. Assess Health

Based on the collected signals, produce a health assessment:

**healthy** — All of:
- Build passing
- Coverage stable or improving
- No new vulnerabilities
- No new errors

**warning** — Any of:
- Coverage declining (but still above threshold)
- Minor new vulnerabilities (low severity)
- Build time increasing significantly

**degraded** — Any of:
- Build failing
- Coverage dropped below threshold
- High/critical vulnerabilities found
- New test failures

### 9. Generate Actionable Items

For each concern, generate a concrete actionable item:

| Concern | Actionable Item |
|---------|----------------|
| Coverage dropped in module X | "Add tests for functions Y, Z in module X" |
| Flaky test detected | "Investigate intermittent failure in test_foo" |
| New vulnerability in package P | "Update package P to version V or find alternative" |
| Build time increased 30% | "Profile build pipeline, check for new heavy dependencies" |

### 10. Write Report

Write `.sprint/monitoring-report.yaml`:

```yaml
phase: 12
phase_name: monitoring
role: sre
status: complete
timestamp: <ISO timestamp>
depends_on: merge_deploy

summary: |
  <1-3 sentence summary of post-merge health>

merge_context:
  pr_number: <number>
  pr_url: <url>
  merge_commit: <sha>
  target_branch: <branch>

measurements:
  build:
    status: success|failure
    duration_seconds: <number>
    compared_to_average: faster|normal|slower|unknown

  tests:
    total: <count>
    passing: <count>
    failing: <count>
    skipped: <count>
    new_tests_added: <count>|unknown
    flaky_tests:
      - <test name if any>

  coverage:
    current: <percentage>
    previous: <percentage>|unknown
    delta: <+/- percentage>|unknown
    trend: improving|stable|declining|unknown
    uncovered_critical_paths:
      - <path if any>

  errors:
    new_errors_in_ci: <count>
    error_types:
      - <type if any>

  performance:
    build_time_delta: <seconds>|unknown
    test_time_delta: <seconds>|unknown

  dependencies:
    new_vulnerabilities: <count>
    outdated_packages: <count>|unavailable

health_assessment:
  overall: healthy|warning|degraded
  concerns:
    - <item>
  improvements:
    - <item>

actionable_items:
  - type: <coverage_regression|flaky_test|vulnerability|performance|error>
    description: "<what happened>"
    suggested_action: "<what to do>"

outputs:
  - .sprint/monitoring-report.yaml

open_issues: []

signals:
  pass: <true if healthy>
  confidence: <high if all signals collected, medium if some unavailable>
  blockers: []
```

## Trend Lookback Window

When computing deltas and trends, compare current signals against recent history. The lookback window determines how far back to look.

### Default: Last 5 Workflow Runs

```bash
# Fetch last 5 CI runs for trend comparison
gh run list --branch <target-branch> --limit 5 --json status,conclusion,createdAt,updatedAt
```

Use these runs to compute:
- `build.compared_to_average`: average duration of last 5 runs vs current
- `performance.build_time_delta`: current vs average of last 5
- `tests.flaky_tests`: tests that failed in any of last 5 but passed in others

### Coverage Trend

For coverage comparison, use the most recent available source:
1. `.sprint/qa-report.yaml` from this sprint (Phase 9) — primary source
2. Previous sprint's `monitoring-report.yaml` if available — for cross-sprint trends
3. If neither exists, report `unknown` and note "first measurement — establishing baseline"

### Configuration

Override the lookback window in `.sprint/config.yaml`:

```yaml
signal_collection:
  trend_lookback_runs: 5       # Number of CI runs to compare against (default: 5)
  trend_lookback_days: 30      # Alternative: look back N days instead of N runs
  coverage_source: qa_report   # qa_report | previous_sprint | both
```

If `trend_lookback_runs` is set, use run count. If `trend_lookback_days` is set instead, filter runs by date. If both are set, `trend_lookback_runs` takes precedence.

### First Sprint Handling

When no historical data exists:
- Set all trend fields to `unknown`
- Set `compared_to_average` to `unknown`
- Note in summary: "First sprint — establishing baselines for future comparison"
- All current measurements become the baseline for the next sprint

## Design Principles

- **Real signals only.** Every data point comes from a command output or file. No guessing.
- **Deltas over absolutes.** "Coverage dropped 2%" is more useful than "Coverage is 78%."
- **Graceful degradation.** If a tool isn't available (no pip-audit, no CI runs), skip that section and note it as `unavailable`. Don't fail the whole collection.
- **Actionable.** Every concern has a suggested fix.

## Composition

- **Consumed by:** `commands/sprint-run.md` (Phase 12)
- **Feeds into:** `skills/sprint-retrospective/` and `skills/feedback-synthesizer/` (Phase 13)
- **Reads from:** `.sprint/merge-report.yaml` (Phase 11), CI/CD systems (gh CLI)
- **Writes to:** `.sprint/monitoring-report.yaml`
