# Scenario 09c: Refactoring and Codebase Health

## Features Exercised

- Commands: `/refactor-clean`, `/health-check`
- Agents: refactor-cleaner

## Prerequisites

Scenarios 04-08 completed (multiple modules built, some dead code and
accumulated TODOs from rapid development).

## Prompts

### Prompt 09c-A: Dead Code Cleanup

```text
Clean up the codebase. Look for dead code, unused imports, functions that
could be consolidated, and leftover TODO comments.

Use /refactor-clean.
```

**What Should Happen:**
- Claude invokes `/refactor-clean` which spawns the refactor-cleaner agent.
- Scans for:
  - Dead code: unused functions, unreachable branches
  - Unused imports
  - Redundant code that can be consolidated
  - TODO comments that should be resolved or tracked
  - Print statements (should be logging)
- Makes targeted cleanups.
- Runs tests after each change.

**Checkpoint:** Codebase is cleaner. Dead code removed. All tests still pass.
Diff shows only removals and consolidations, no new features.

---

### Prompt 09c-B: Consolidation Pass

```text
Are there any repeated patterns across modules that could be extracted into
shared utilities? For example, all route files probably have similar error
handling boilerplate.

/refactor-clean
```

**What Should Happen:**
- Identifies patterns duplicated across modules:
  - Error handling in each route file
  - Validation patterns in each service
  - Test fixture setup patterns
- Suggests or implements consolidation into shared utilities.

**Checkpoint:** Shared patterns extracted. Module code simplified. All tests
still pass.

---

### Prompt 09c-C: Quick Health Check

```text
/health-check quick
```

**What Should Happen:**
- Fast codebase health scan: dependency versions, import health, basic
  code metrics.

**Checkpoint:** Quick health summary.

---

### Prompt 09c-D: Full Health Check

```text
Run a full health check on this codebase. Check dependencies, code quality,
test coverage, integration health, and overall project hygiene.

Use /health-check.
```

**What Should Happen:**
- Claude invokes `/health-check` which runs a parallel codebase health audit.
- Checks:
  - Dependency health: outdated packages, security advisories, unused deps
  - Code health: complexity metrics, function sizes, nesting depth
  - Test health: coverage percentage, test-to-code ratio, slow tests
  - Integration health: imports resolve, no circular dependencies
  - Project hygiene: stale branches, uncommitted changes, TODO count
- Produces an overall health score with actionable findings.

**Checkpoint:** Health report with score. Findings grouped by category.
Each finding has severity and recommended action.

---

### Prompt 09c-E: Dependency Health Check

```text
/health-check dependencies
```

**What Should Happen:**
- Focused dependency analysis: pip-audit style vulnerability check,
  version currency, unused dependencies.

**Checkpoint:** Dependency report with specific upgrade recommendations.

---

### Prompt 09c-F: Integration Health Check

```text
/health-check integrate
```

**What Should Happen:**
- Checks cross-module integration: are all blueprints registered? Do all
  imports resolve? Are there circular dependencies?

**Checkpoint:** Integration report. Any broken imports or registration
issues identified.
