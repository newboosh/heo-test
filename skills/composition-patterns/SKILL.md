---
name: composition-patterns
description: Reference patterns for composing skills and commands. Use when designing new skills that delegate, chain, or orchestrate other skills.
model: opus
user-invocable: true
---

# Composition Patterns

**You are designing a new skill or command.** Apply these patterns to create composable, maintainable workflows.

## Skill vs Command

| Type | Purpose | When to Use |
|------|---------|-------------|
| **Skill** | Reference, guidance, knowledge | Agent needs context or patterns to apply |
| **Command** | Action, workflow, side effects | User invokes to do something |

**Rule of thumb:** If it *does* something, it's a command. If it *informs* how to do something, it's a skill.

## Core Principle: Prefer Decomposition

**Always decompose large workflows into smaller, focused units.**

Instead of:
```
/big-workflow
    ├─► 50 lines of auth logic
    ├─► 80 lines of validation
    ├─► 60 lines of processing
    └─► 40 lines of cleanup
```

Decompose into:
```
/big-workflow
    ├─► /auth-setup        ← reusable
    ├─► /validate          ← reusable
    ├─► /process           ← focused
    └─► /cleanup           ← reusable
```

**Benefits of decomposition:**
- Each piece is testable independently
- Reuse across multiple workflows
- Easier to understand and maintain
- Single responsibility per unit
- Fix once, benefit everywhere

**When NOT to decompose:**
- Logic is truly one-off (no reuse potential)
- Overhead exceeds benefit (< 10 lines)
- Tight coupling makes separation artificial

## Document Sizing

**Target sizes for maintainability:**

| Document Type | Target Lines | Max Lines | Action if Exceeded |
|---------------|--------------|-----------|-------------------|
| Command (simple) | 50-80 | 100 | Consider if it does too much |
| Command (orchestrator) | 80-120 | 150 | Decompose into subcommands |
| Skill | 100-200 | 400 | Split into focused skills |
| Agent | 100-150 | 200 | Extract common patterns |

**Size thresholds:**
- **< 50 lines**: Probably fine as-is
- **50-100 lines**: Good working size
- **100-200 lines**: Review for decomposition opportunities
- **200+ lines**: Strongly consider splitting

**Signs a document is too large:**
- Multiple distinct responsibilities
- Repeated patterns that could be extracted
- Sections that work independently
- Hard to find specific information

## Documentation Guidelines

**Write documentation that is effective and relevant.**

### Active Voice Opening

Start every skill/command with a directive:

```markdown
# Good
**You are processing CodeRabbit comments.** Apply fixes and push changes.

# Avoid
This command processes CodeRabbit comments.
```

### Structure for Scannability

Use consistent heading hierarchy:

```markdown
## Overview          ← What this does (1-2 sentences)
## Arguments         ← What inputs it takes
## Instructions      ← Step-by-step workflow
## Error Handling    ← What can go wrong
## Used By           ← Composition context (if applicable)
```

### Show Composition Relationships

When a command delegates or is delegated to, document it:

```markdown
## Composition

This command delegates to:
- `/sub-command-a` - for X
- `/sub-command-b` - for Y

## Used By

Called by `/parent-command` as Step 2.
```

### Keep Examples Minimal but Complete

```markdown
# Good - Shows the pattern clearly
` ` `bash
git commit -m "fix: description"
` ` `

# Avoid - Too much irrelevant detail
` ` `bash
# First check if we're in a git repo
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Get the current branch
    BRANCH=$(git branch --show-current)
    # Make sure we're not on main
    if [ "$BRANCH" != "main" ]; then
        # Now we can commit
        git commit -m "fix: description"
    fi
fi
` ` `
```

### Reference, Don't Repeat

Instead of duplicating patterns, reference shared documentation:

```markdown
# Good
Run quality checks (see `common-patterns.md`):
` ` `bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
` ` `

# Avoid
Copy-pasting 20 lines of quality check logic
```

## Pattern Catalog

### 1. Delegation Pattern

One skill delegates a specific responsibility to another, avoiding duplication.

```
/parent
    ├─► own setup
    ├─► /child           ← delegate specific step
    └─► own cleanup
```

**When to use:**
- Shared logic exists in another skill
- You want single source of truth
- The delegated step is self-contained

**Implementation:**
```markdown
## Step 3: Push Changes

Delegate to `/push`:

` ` `
/push
` ` `

The `/push` command handles auth, quality checks, and PR creation.
```

**Examples:**
- `/coderabbit` → `/push` (for pushing fixes)
- `/build-fix` → `/verify quick` (for error detection)
- `/tdd` → `/test-coverage` (for gap analysis)

---

### 2. Pipeline Pattern

Skills chain sequentially, each step's output feeding the next.

```
/pipeline
    ├─► /step-1 → data
    │       ↓
    ├─► /step-2 → transformed
    │       ↓
    └─► /step-3 → final result
```

**When to use:**
- Linear transformation of data/state
- Each step has clear input/output contract
- Steps are independently useful

**Implementation:**
```markdown
## Pipeline

1. **Analyze**: `/test-coverage` → gap list
2. **Generate**: For each gap, write tests
3. **Verify**: `/verify quick` → confirm passing
```

**Data flow options:**
- **Implicit**: Next step reads from filesystem/git
- **Explicit**: Document expected state between steps
- **Variable**: Store in memory, pass as argument

---

### 3. Gate Pattern

A skill acts as a pass/fail checkpoint before allowing progression.

```
/workflow
    ├─► /gate ─┬─► PASS → continue
    │          └─► FAIL → stop with reason
    └─► /next-step (only if gate passed)
```

**When to use:**
- Quality enforcement before risky operations
- Validation before side effects
- Go/no-go decisions

**Implementation:**
```markdown
## Step 2: Quality Gate

Run verification:

` ` `bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
` ` `

- **PASS**: Continue to Step 3
- **FAIL**: Stop. Fix issues before proceeding.
```

**Gate types:**
- **Hard gate**: Must pass to continue
- **Soft gate**: Warn but allow override
- **Advisory gate**: Inform only, no blocking

---

### 4. Loop Pattern

A skill iterates until a termination condition is met.

```
/loop
    ┌─► check exit condition
    │   ├─► MET → exit with summary
    │   └─► NOT MET ↓
    ├─► /work-step
    ├─► wait/verify
    └───────┘ repeat
```

**When to use:**
- Async workflows (waiting for external response)
- Iterative refinement until quality target
- Processing queues

**Implementation:**
```markdown
## Loop Structure

Configuration:
- **MAX_ITERATIONS**: 8
- **WAIT_INTERVAL**: 2 minutes

Loop:
1. Check exit conditions (clean/max iterations/signal)
2. Process work item
3. Wait for external verification
4. Repeat or exit
```

**Exit conditions (check in order):**
1. Success condition met
2. Max iterations reached
3. External stop signal
4. Unrecoverable error

---

### 5. Alias Pattern

A skill is a thin wrapper providing semantic clarity without new logic.

```
/specific-intent
    └─► /general-command $ARGUMENTS
```

**When to use:**
- Same logic, different user intent
- Preset arguments for common cases
- Discoverability for specific use cases

**Implementation:**
```markdown
---
name: push-new
description: Push a new branch to remote (alias for /push)
---

# Push New Branch

Delegate to `/push`:

` ` `
/push $ARGUMENTS
` ` `

The `/push` command auto-detects new branches.
```

**Alias vs Fork:**
- **Alias**: Same behavior, different name
- **Fork**: Modified behavior, shared ancestry

---

### 6. Composition Pattern

A skill orchestrates multiple sub-skills, aggregating results.

```
/orchestrator
    ├─► /skill-a ──┐
    ├─► /skill-b ──┼─► aggregate
    └─► /skill-c ──┘
        │
        ▼
    unified report
```

**When to use:**
- Comprehensive analysis from multiple angles
- Parallel independent checks
- Building higher-level workflows from primitives

**Implementation:**
```markdown
## Composed Skills

| Skill | Purpose |
|-------|---------|
| `diff-review` | Scope changes |
| `standards-lookup` | Find rules |
| `compliance-check` | Verify rules |
| `artifact-audit` | Check completeness |

Run all, then aggregate into unified report.
```

**Aggregation strategies:**
- **Merge**: Combine all outputs
- **Priority**: Most severe finding wins
- **Consensus**: Require agreement

---

### 7. Fallback Pattern

Try primary approach; if it fails, fall back to alternative.

```
/resilient
    ├─► try /primary
    │   ├─► SUCCESS → done
    │   └─► FAIL ↓
    └─► try /fallback
        ├─► SUCCESS → done
        └─► FAIL → report both failures
```

**When to use:**
- Environment-dependent tools
- Optional enhancements
- Graceful degradation

**Implementation:**
```markdown
## Verification

Try project-specific checks:
` ` `bash
make quality 2>/dev/null
` ` `

If not available, fall back to generic:
` ` `bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-quality-checks.sh"
` ` `
```

---

### 8. Decorator Pattern

Wrap a skill with pre/post behavior without modifying it.

```
/decorated
    ├─► pre-hook (setup, validation)
    ├─► /core-skill
    └─► post-hook (cleanup, logging)
```

**When to use:**
- Adding logging/metrics
- Auth/validation wrappers
- Cleanup guarantees

**Implementation:**
```markdown
## Workflow

### Pre-flight
` ` `bash
source "${CLAUDE_PLUGIN_ROOT}/scripts/github-auth.sh" && github_auth_setup
` ` `

### Core
/push

### Post-flight
` ` `bash
gh pr view --json state,url
` ` `
```

---

## Choosing a Pattern

| Situation | Pattern |
|-----------|---------|
| Reusing existing skill logic | Delegation |
| Sequential transformation | Pipeline |
| Quality enforcement | Gate |
| Waiting for external events | Loop |
| Same logic, clearer name | Alias |
| Multi-perspective analysis | Composition |
| Optional/environment-specific | Fallback |
| Adding cross-cutting concerns | Decorator |
| Multi-phase pipeline with persistent state | Handoff Protocol |

## Combining Patterns

Patterns compose naturally:

```
/complex-workflow
    ├─► Gate: /verify quick
    ├─► Loop:
    │   ├─► Delegation: /coderabbit
    │   ├─► wait
    │   └─► check condition
    └─► Decorator: post-summary
```

---

### 9. Handoff Protocol Pattern

A standardized context-passing contract between sequential phases. Every phase reads the previous handoff, does its work, and writes its own handoff.

```
Phase N                          Phase N+1
   │                                │
   ├─► Read .sprint/prev.yaml       │
   ├─► Do work                      │
   ├─► Write .sprint/current.yaml ──►  Read .sprint/current.yaml
   │                                ├─► Do work
   │                                ├─► Write .sprint/next.yaml
```

**When to use:**
- Multi-phase pipelines where each phase is a different agent/skill/command
- State must persist across tool boundaries (different sessions, different agents)
- You need resumability — any phase can restart from its input handoff

**Standard handoff fields:**

```yaml
# Every handoff file includes these fields:
phase: <phase number>
phase_name: <phase name>
role: <role that produced this>
status: complete | failed | blocked
timestamp: <ISO timestamp>
depends_on: <previous phase name>

summary: |
  <1-3 sentence summary of what this phase produced>

outputs:
  - <list of artifacts produced>

open_issues:
  - <unresolved items for downstream phases>

signals:
  pass: <true/false>
  confidence: <high/medium/low>
  blockers: []
```

**Phase-specific fields** extend the standard fields with whatever that phase produces (e.g., user stories, test results, review findings).

**State directory:** All handoffs live in `.sprint/`. See `docs/SPRINT_LIFECYCLE.md` for the full directory layout.

**Key properties:**
- **Filesystem-based**: No hidden state. Human-readable YAML files.
- **Phase independence**: Each phase reads only from previous handoffs, not internal state. Phases can be re-run independently.
- **Resumability**: Read `current_phase` from `.sprint/sprint-meta.yaml` to resume from last completed phase.

---

## Anti-Patterns

**Avoid:**
- **Monolithic commands**: If > 100 lines, decompose
- **Deep nesting**: Max 2-3 levels of delegation
- **Circular delegation**: A → B → A
- **Hidden side effects**: Document what each skill modifies
- **Implicit contracts**: Be explicit about expected state
- **Duplicated logic**: If you copy-paste, extract to shared skill

## Documentation Template

When using composition, document:

```markdown
## Composed From

| Skill | Purpose | Required |
|-------|---------|----------|
| `/skill-a` | Does X | Yes |
| `/skill-b` | Does Y | Optional |

## Data Flow

1. `/skill-a` produces: file list
2. `/skill-b` consumes: file list, produces: report
```

---

## Action Checklist

**Before creating a new skill or command, verify:**

- [ ] **Decomposition**: Can this be broken into smaller pieces?
- [ ] **Existing skills**: Does something already do part of this? Delegate to it.
- [ ] **Pattern fit**: Which composition pattern applies?
- [ ] **Reuse potential**: Will other workflows need this logic? Extract it.
- [ ] **Single responsibility**: Does this do exactly one thing well?

**After creating:**

- [ ] **Documentation**: Is the composition documented?
- [ ] **Data flow**: Are inputs/outputs between steps clear?
- [ ] **Error handling**: What happens when a delegated step fails?
