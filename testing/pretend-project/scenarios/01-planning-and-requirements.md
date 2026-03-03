# Scenario 01: Planning and Requirements

## Features Exercised

- Commands: `/plan`, `/context`, `/standards`, `/task`,
  `/problem-definition`, `/requirements-engineering`
- Skills: plan-context, problem-definition, requirements-engineering,
  boundary-critique, standards-lookup
- Agents: planner, context-agent

## Prerequisites

Scenario 00 completed (plugin configured, catalog built).

## Prompts

### Prompt 01-A: Define the Problem

```text
I need to build a collaborative task management API. Before we start coding,
help me define the problem clearly. What are we actually solving? Who are the
users? What are the constraints?

Use /problem-definition to think this through.
```

**What Should Happen:**
- Claude invokes the problem-definition skill.
- It produces a structured problem statement covering: user personas, core
  problem, constraints, success criteria, out-of-scope items.
- The boundary-critique skill may be referenced to challenge assumptions.

**Checkpoint:** A problem definition document is produced. It identifies at
least: API consumers (frontend app, mobile), admin users, team leads. It
flags constraints like auth requirements, multi-tenancy, and rate limits.

---

### Prompt 01-B: Requirements Engineering

```text
Now let's get detailed requirements. I need:
- User registration and login (JWT)
- Workspaces where teams collaborate
- Tasks with title, description, priority, due date, assignee
- Comments on tasks
- Real-time notifications when tasks change
- Background email digests

Use /requirements-engineering to structure this properly.
```

**What Should Happen:**
- Claude invokes the requirements-engineering skill.
- It produces structured requirements: functional, non-functional, data
  model, API contracts, acceptance criteria.
- It may invoke boundary-critique to challenge scope boundaries.

**Checkpoint:** Requirements document with numbered items. Each requirement
has acceptance criteria. The document distinguishes must-have vs nice-to-have.

---

### Prompt 01-C: Gather Context

```text
Before we plan the implementation, gather context on the current state of
this project. What exists, what's missing, what patterns are already
established?

Use /context to do a thorough scan.
```

**What Should Happen:**
- Claude invokes `/context` which spawns the context-agent.
- The agent explores the codebase: reads all files, maps dependencies,
  identifies patterns (factory app, blueprint routing, SQLAlchemy models).
- Returns a structured context report.
- The plan-context skill provides current plan/todo state.

**Checkpoint:** Context report lists all existing files with summaries.
Identifies the app factory pattern, blueprint registration, SQLAlchemy usage.
Notes missing pieces: no auth routes, no task model, no Celery config.

---

### Prompt 01-D: Look Up Standards

```text
What coding standards should we follow for this Flask project?
```

**What Should Happen:**
- Claude invokes `/standards` which triggers the standards-lookup skill.
- Returns project-specific standards from project-standards.yaml (if created
  in 00-B) and general Python/Flask conventions from the plugin's standards.

**Checkpoint:** Standards output includes Python style rules, naming
conventions, test naming patterns, and Flask-specific patterns.

---

### Prompt 01-E: Plan the Architecture

```text
Plan the full implementation. Break it into features that can be developed
independently and in parallel. Consider what order makes sense — some
features depend on others.

Use /plan to create a thorough implementation plan.
```

**What Should Happen:**
- Claude invokes `/plan` which enters plan mode and spawns the planner agent.
- The planner reads context, requirements, and standards.
- Produces a phased implementation plan with:
  - Feature breakdown (auth, tasks, workspaces, comments, notifications, jobs)
  - Dependency graph (auth first, then tasks, then workspaces, etc.)
  - File-level changes per feature
  - Risk assessment
- Uses the /task 4-phase workflow if invoked.

**Checkpoint:** Implementation plan exists with 5-7 features, dependency
ordering, and estimated file changes per feature. Auth is identified as the
foundational feature.

---

### Prompt 01-F: Task Workflow (Optional)

```text
Use /task to create a detailed task breakdown for the authentication module.
```

**What Should Happen:**
- Claude invokes `/task` which runs the 4-phase workflow:
  Phase 1: Discovery — understand what exists
  Phase 2: PRD — product requirements for auth
  Phase 3: Tasks — granular task breakdown
  Phase 4: Execution plan — ordered implementation steps

**Checkpoint:** Task breakdown with 8-12 sub-tasks for the auth module.
Each task has clear acceptance criteria.
