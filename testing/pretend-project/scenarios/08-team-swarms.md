# Scenario 08: Team Swarms and Orchestration

## Features Exercised

- Commands: `/plan-swarm`, `/test-swarm`, `/review-swarm`, `/orchestrate`,
  `/tree conflict`, `/tree reset incomplete`
- Skills: team-patterns, sub-agent-dispatch, gate-decision
- Agents: (multiple, via swarms)
- Hooks: sentinel-task-context (auto), post_agent_work (auto)

## Prerequisites

Scenarios 04-06 completed (auth implemented, reviewed). Ideally have the
task CRUD worktree with some implementation too.

## Prompts

### Prompt 08-A: Plan Swarm

```text
We need to plan the next sprint. Run a parallel planning session to evaluate
the remaining features: workspaces, comments, notifications, and background
jobs. Have multiple agents assess scope and dependencies simultaneously.

Use /plan-swarm.
```

**What Should Happen:**
- Claude invokes `/plan-swarm` which spawns multiple planning agents.
- Agents work in parallel:
  - Agent 1: Workspace feature scope and design
  - Agent 2: Comments feature scope and design
  - Agent 3: Notifications architecture (builds on the ADR from scenario 02)
  - Agent 4: Background jobs scope
- Results consolidated into a unified sprint plan.
- The sentinel-task-context hook fires before each subagent spawn, capturing
  orchestrator intent.
- The post_agent_work hook fires when each agent completes.

**Checkpoint:** Consolidated plan from multiple agents. Dependencies mapped.
Sprint backlog for sprint 2 created.

---

### Prompt 08-B: Test Swarm

```text
We have the auth module and part of the task module implemented. Spawn a team
to write tests across different domains simultaneously.

Use /test-swarm to cover: auth edge cases, task CRUD, and integration tests.
```

**What Should Happen:**
- Claude invokes `/test-swarm` which spawns test-writing agents by domain.
- Each agent writes tests for its assigned domain:
  - Auth agent: edge cases (token expiry, malformed tokens, concurrent login)
  - Task agent: CRUD operations, validation, authorization
  - Integration agent: cross-module flows (register → login → create task)
- Tests follow the naming standard from standards/TEST_NAMING.md.
- Results merged without conflicts.

**Checkpoint:** New test files created across domains. All tests pass. No
naming collisions. Coverage improved.

---

### Prompt 08-C: Review Swarm

```text
Review the auth and task modules from multiple perspectives simultaneously.
Get security, performance, and maintainability reviews in parallel.

Use /review-swarm.
```

**What Should Happen:**
- Claude invokes `/review-swarm` which spawns review agents with different
  focus areas:
  - Security reviewer: auth vulnerabilities, input validation
  - Performance reviewer: query efficiency, caching opportunities
  - Maintainability reviewer: code organization, naming, abstraction
- Each agent produces a focused review.
- Results consolidated with severity rankings.

**Checkpoint:** Multi-perspective review document. Findings categorized by
perspective and severity.

---

### Prompt 08-D: Gate Decision

```text
Based on the review results, should we proceed to merge the auth module?
Give me a go/no-go decision.
```

**What Should Happen:**
- The gate-decision skill evaluates readiness criteria:
  - Tests passing? Coverage adequate?
  - Security issues resolved?
  - Code review approved?
  - Documentation complete?
- Produces a go/no-go recommendation with rationale.

**Checkpoint:** Decision output with clear rationale and any blocking items.

---

### Prompt 08-E: Orchestrate Execution

```text
/orchestrate phase 7
```

**What Should Happen:**
- Claude invokes `/orchestrate` for a specific execution phase.
- Phase 7 is the review phase in the sprint lifecycle.
- Runs the review workflow for the current sprint's implementation.

**Checkpoint:** Phase 7 artifacts produced (review results).

---

### Prompt 08-F: Conflict Analysis

```text
I've been working in both the auth and task worktrees. Check if they have
conflicting changes before I try to merge either.

Use /tree conflict.
```

**What Should Happen:**
- Claude invokes `/tree conflict` which analyzes potential merge conflicts
  between worktree branches.
- Checks for overlapping file changes (both probably touch app.py to register
  blueprints, both may modify models/__init__.py).
- Reports conflict probability and specific files.

**Checkpoint:** Conflict report identifying shared files. Suggests merge
order to minimize conflicts.

---

### Prompt 08-G: WIP Save

```text
I need to pause work on the workspace feature. Save it as work-in-progress.

/tree reset incomplete
```

**What Should Happen:**
- Claude invokes `/tree reset incomplete` in the workspace worktree.
- Commits current work with a WIP prefix.
- Pushes to remote.
- Writes a synopsis of work completed so far.
- Does NOT do the full 6-phase reset (no AI wrapup, no mechanical cleanup).

**Checkpoint:** WIP commit exists on the workspace branch. Synopsis saved.
Worktree still exists for later resumption.
