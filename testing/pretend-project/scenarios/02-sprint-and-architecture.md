# Scenario 02: Sprint Planning and Architecture Decisions

## Features Exercised

- Commands: `/sprint`, `/sprint-run`, `/sprint-run status`, `/arch-debate`
- Skills: sprint, backend-patterns, process-map
- Agents: architect

## Prerequisites

Scenario 01 completed (requirements and plan exist).

## Prompts

### Prompt 02-A: Sprint Planning

```text
Let's plan our first sprint. The goal is to implement user authentication
and the core task CRUD. We have the requirements from the previous session.

Use /sprint to plan this sprint.
```

**What Should Happen:**
- Claude invokes `/sprint` which triggers the sprint skill.
- Runs phases 1-5:
  1. Intake and triage — pulls from requirements
  2. Refinement — breaks features into stories
  3. Design — technical design for auth + tasks
  4. Technical planning — identifies implementation details
  5. Backlog — ordered sprint backlog
- The process-map skill identifies affected business processes and data
  structures.
- The backend-patterns skill informs API design and database modeling.

**Checkpoint:** Sprint backlog exists with ordered stories. Stories have
acceptance criteria and estimated complexity. Auth stories come before task
stories.

---

### Prompt 02-B: Architecture Debate

```text
For real-time notifications, we need to decide between WebSockets, Server-
Sent Events (SSE), and long polling. Each has trade-offs for our Flask/Celery
stack. Debate the options and produce an Architecture Decision Record.

Use /arch-debate "notification transport" approaches "WebSocket,SSE,Polling"
```

**What Should Happen:**
- Claude invokes `/arch-debate` which spawns the architect agent (or multiple
  agents in a swarm pattern).
- Each approach is argued with pros/cons specific to the Flask/Celery stack:
  - WebSocket: bidirectional but needs flask-socketio, complicates deployment
  - SSE: simple, HTTP-based, good for one-way updates, native browser support
  - Polling: simplest but wasteful, higher latency
- An ADR (Architecture Decision Record) is produced with:
  - Context, options considered, decision, consequences.

**Checkpoint:** ADR document recommending one approach with clear rationale.
The recommendation should account for the Celery worker architecture and
Redis pub/sub availability.

---

### Prompt 02-C: Full Sprint Lifecycle (Optional)

```text
Run the full sprint lifecycle for this sprint — from planning through
retrospective.

Use /sprint-run attended to run all 13 phases with my approval at each gate.
```

**What Should Happen:**
- Claude invokes `/sprint-run attended` which orchestrates all 13 phases:
  1-5. Planning (already done in 02-A, may skip or summarize)
  6-7. Implementation and review
  8. QA validation
  9. Security review
  10. PR and CI gates
  11. Merge
  12. Post-merge monitoring
  13. Retrospective
- At each phase gate, it pauses for user approval.
- `/sprint-run status` can be used to check progress at any time.

**Checkpoint:** Sprint status shows current phase. Each completed phase has
artifacts. This is a long-running scenario that spans multiple sessions.

**Note:** This prompt exercises the sprint machinery. The actual implementation
work happens in scenarios 03-08. Use this to verify the sprint orchestration
framework works, even if the implementation phases are simplified.
