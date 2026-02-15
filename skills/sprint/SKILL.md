---
name: sprint
description: Full sprint lifecycle — from developer requirements through planning, implementation, review, CI/CD, monitoring, and retrospective. Entry point for automated development cycles.
argument-hint: [what to build]
disable-model-invocation: true
---

# Sprint Skill

Entry point for the automated sprint lifecycle. Handles the planning half (Phases 1-5), then delegates execution and review (Phases 6-11) to the orchestrate command. Monitoring and retrospective (Phases 12-13) run after merge.

**Full lifecycle:** See `docs/SPRINT_LIFECYCLE.md` for the 13-phase reference.

## Flow

```text
Intake → Refinement → Design → Technical Planning → Backlog → [orchestrate] → Monitoring → Retrospective
  1          2           3            4                5         6-11             12            13
```

This skill directly manages Phases 1-5. Phases 6-11 delegate to `/orchestrate`. Phases 12-13 are handled by the Sprint Runner (see lifecycle doc).

## Velocity Mode Behavior

This skill reads `velocity_mode` from `.sprint/sprint-meta.yaml` to determine how to interact. The Sprint Runner sets this before invoking the sprint skill.

| Decision Point | Autonomous (default) | Attended |
|----------------|---------------------|----------|
| Feedback carry-forward | Auto-include critical items | Ask developer which to include |
| Requirements gathering | Infer from input text + codebase | Ask clarifying questions |
| Phase checkpoints | Auto-continue | Ask to continue/edit/restart |
| Edit subcommand | N/A (not invoked) | Interactive editing |
| Rollback | N/A (not invoked) | Interactive with confirmation |

**Key rule:** In autonomous mode, this skill NEVER uses `AskUserQuestion`. All decisions are made from available data. Ambiguities are noted in `open_issues` for downstream phases to handle.

## Commands

- `/sprint <what to build>` - Run Phases 1-5 (pipeline mode, auto-continues)
- `/sprint phase <N>` - Run a single planning phase (1-5) and return control
- `/sprint` (bare) - Smart router: show current state, offer contextual choices
- `/sprint status` - Quick non-interactive status check
- `/sprint reset` - Clear sprint state and start over
- `/sprint edit <phase>` - Edit a completed phase's output and re-validate
- `/sprint rollback [phase]` - Revert to a previous phase, removing downstream outputs
- `/sprint export-issues` - Export backlog tasks as GitHub issues

## Phase Overview

| Phase | Role | Output | Owner |
|-------|------|--------|-------|
| 1. Intake | Developer provides requirements | `.sprint/input.yaml` | This skill |
| 2. Refinement | Translate to user stories | `.sprint/product.yaml` | This skill |
| 3. Design | Define UX/API requirements | `.sprint/design.yaml` | This skill |
| 4. Technical Planning | Plan architecture | `.sprint/technical.yaml` | This skill |
| 5. Backlog | Create task list | `.sprint/backlog.yaml` | This skill |
| 6-11. Execution → Merge | Implement, review, CI, merge | multiple | `/orchestrate` |
| 12-13. Monitor → Retro | Signals, learnings, feedback | multiple | Sprint Runner |

---

## Execution

### Parse Command

```text
If $ARGUMENTS is empty:
  → Smart Router (see below)
If $ARGUMENTS is "status":
  → Quick status check (non-interactive)
If $ARGUMENTS is "reset":
  → Clear .sprint/ directory
If $ARGUMENTS starts with "edit":
  → Edit specified phase output (see Edit Subcommand section)
If $ARGUMENTS starts with "rollback":
  → Rollback to specified phase (see Rollback section)
If $ARGUMENTS is "export-issues":
  → Export backlog to GitHub issues (see Export Issues section)
If $ARGUMENTS starts with "phase":
  → Parse phase number N from "phase <N>"
  → Validate N is 1-5 (this skill manages planning phases only)
  → If N not in 1-5: "Phase {N} is outside the planning range (1-5).
     Use /orchestrate phase {N} for execution phases (6-11),
     or /sprint-run for the full lifecycle."
  → Run Phase N only (see Single Phase Execution below)
Otherwise:
  → Start Phase 1 with $ARGUMENTS as initial input, then continue through Phase 5
```

### Smart Router (bare `/sprint`)

1. Check if `.sprint/` exists
2. If no sprint in progress:
   - Show "No sprint in progress. Run `/sprint <what to build>` to start."
3. If sprint exists:
   - Read `.sprint/sprint-meta.yaml`
   - Show current phase, status, and summary of last completed phase
   - Offer contextual choices using AskUserQuestion:
     - If current phase is complete and < 13: **"Continue to Phase N+1"**
     - If current phase is blocked/failed: **"Retry current phase"** / **"Roll back to Phase N"**
     - Always: **"View status"** / **"Reset sprint"**
4. Execute the user's choice

### Phase 1: Developer Input (Intake)

**Goal**: Capture what the developer wants to build.

**Process**:
0. **Check for pending feedback** — Before gathering new input, check if a previous sprint left feedback items:

```text
If .sprint/feedback-intake.yaml exists:
  Read the file and check synthesis.items[]

  Read .sprint/sprint-meta.yaml to check velocity_mode.

  If velocity_mode == "autonomous":
    Auto-include all items with priority "critical"
    Skip items with priority high/medium/low
    If any critical items were included:
      - Prepend them to the developer's requirements
      - Note in input.yaml context: "Auto-included N critical items from previous sprint feedback"
      - Move included items to context.prior_feedback: [...]
    Proceed without asking.

  If velocity_mode == "attended":
    Show items with priority critical or high to the developer:

    "Previous sprint generated feedback items:
     - [critical] Fix post-merge build failure in auth module
     - [high] Coverage regression in payments service (82% → 77%)

     Would you like to include any of these in this sprint?"

    Use AskUserQuestion with options:
      - "Include all shown items" → prepend to requirements
      - "Let me pick" → show each item, let developer select
      - "Skip feedback" → proceed with only new requirements

    If items are included:
      - Append them to the developer's requirements
      - Note in input.yaml context: "Includes N items from previous sprint feedback"
      - Move included items to context.prior_feedback: [...]
```

If no feedback file exists, skip this step silently.

1. Parse $ARGUMENTS for initial context
2. Gather requirements — behavior depends on velocity mode:

```text
Read .sprint/sprint-meta.yaml to check velocity_mode.

If velocity_mode == "autonomous":
  Infer all fields from $ARGUMENTS and codebase context:
    - what: extract from the developer's input text
    - why: infer from context (if not stated, use "Developer-requested feature")
    - who: infer from codebase (e.g., "API consumers" for API projects)
    - constraints: scan codebase for tech stack, existing patterns
    - context: use Glob/Grep to find related files and systems
  Do NOT use AskUserQuestion. Work with the information available.
  If critical information is genuinely ambiguous, note it in open_issues.

If velocity_mode == "attended":
  Ask clarifying questions using AskUserQuestion:
    - "What specific functionality are you building?" (what)
    - "Why is this needed? What problem does it solve?" (why)
    - "Who will use this?" (who)
    - "Any constraints (time, tech, scope)?" (constraints)
    - "What existing code/systems does this touch?" (context)
```

3. Write `.sprint/input.yaml`:

```yaml
# .sprint/input.yaml
phase: 1
phase_name: intake
role: developer
status: complete
timestamp: <ISO timestamp>
depends_on: null

summary: |
  <1-3 sentence summary of captured requirements>

what: "<functionality description>"
why: "<business value / problem solved>"
who: "<target users>"
constraints:
  - "<constraint 1>"
  - "<constraint 2>"
context:
  existing_systems:
    - "<system 1>"
  related_files:
    - "<file pattern>"

outputs:
  - .sprint/input.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

4. Show checkpoint (see Checkpoint UX section for behavior per velocity mode)

---

### Phase 2: Refinement (Product Management)

**Goal**: Transform developer input into structured product requirements.

**Process**:
1. Read `.sprint/input.yaml`
2. Generate product artifacts:

```yaml
# .sprint/product.yaml
phase: 2
phase_name: refinement
role: product_manager
status: complete
timestamp: <ISO timestamp>
depends_on: intake

summary: |
  <1-3 sentence summary of product requirements>

epic:
  title: "<Epic title from 'what'>"
  description: "<High-level description>"
  business_value: "<From 'why'>"

user_stories:
  - id: US-001
    as_a: "<from 'who'>"
    i_want: "<capability>"
    so_that: "<benefit>"
    acceptance_criteria:
      - "Given <context>, when <action>, then <result>"
      - "Given <context>, when <action>, then <result>"
    priority: must  # must|should|could|wont

success_metrics:
  - metric: "<Measurable outcome 1>"
    measurement: "<How it is measured>"
  - metric: "<Measurable outcome 2>"
    measurement: "<How it is measured>"

scope:
  in_scope:
    - "<Item 1>"
  out_of_scope:
    - "<Item 1>"

integration_requirements:
  - "<From context.existing_systems>"

outputs:
  - .sprint/product.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

3. Show checkpoint with summary table

---

### Phase 3: Design

**Goal**: Define UX requirements and interaction patterns, or API contracts for backend-only work.

**Process**:
1. Read `.sprint/input.yaml` and `.sprint/product.yaml`
2. **Detect design mode** — Determine whether this is frontend/fullstack or backend-only:

```text
Backend-only indicators (any of these → use API mode):
  - input.yaml context mentions: "API", "service", "backend", "CLI", "pipeline", "worker", "cron"
  - input.yaml constraints include: "no UI", "API only", "backend only", "headless"
  - product.yaml user_stories all reference system actors, not human users
  - product.yaml scope.out_of_scope includes UI/frontend items

Frontend/fullstack indicators (default → use UX mode):
  - input.yaml mentions: "page", "form", "button", "UI", "dashboard", "screen"
  - product.yaml user_stories reference human user interactions
```

If backend-only: set `design_mode: backend`, use `skills/sprint/templates/design-api.yaml` as reference, generate API contracts, data flows, error handling, and operational specs.

If frontend/fullstack: set `design_mode: frontend` (default), use `skills/sprint/templates/design.yaml` as reference, generate UX flows, components, validations.

3. Generate design artifacts:

**For frontend/fullstack mode (`design_mode: frontend`):**

```yaml
# .sprint/design.yaml
phase: 3
phase_name: design
role: ux_designer
status: complete
timestamp: <ISO timestamp>
depends_on: refinement

summary: |
  <1-3 sentence summary of design decisions>

design_mode: frontend

ux_requirements:
  flows:
    - name: "<Flow name>"
      trigger: "<What starts this flow>"
      steps:
        - step: 1
          action: "<User action>"
          response: "<System response>"
          next: 2
        - step: 2
          action: "<User action>"
          response: "<System response>"

  components:
    - name: "<Component name>"
      type: form|display|navigation|modal|notification
      purpose: "<What it does>"
      states:
        - default: "<Default state>"
        - loading: "<Loading state>"
        - error: "<Error state>"
        - success: "<Success state>"

  validations:
    - field: "<Field name>"
      rules:
        - required: true
        - pattern: "<regex if applicable>"
        - min_length: <number>
      error_messages:
        invalid: "<Error message>"
        required: "<Required message>"

  accessibility:
    - "<WCAG requirement>"

  edge_cases:
    - scenario: "<Edge case description>"
      handling: "<How to handle>"

outputs:
  - .sprint/design.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

**For backend-only mode (`design_mode: backend`):**

```yaml
# .sprint/design.yaml (backend mode)
phase: 3
phase_name: design
role: api_designer
status: complete
timestamp: <ISO timestamp>
depends_on: refinement

summary: |
  <1-3 sentence summary of API/service design>

design_mode: backend

api_contract:
  base_path: "<base URL path>"
  authentication: "<auth method>"
  endpoints:
    - method: GET|POST|PUT|DELETE
      path: "<endpoint path>"
      description: "<what it does>"
      auth: required|optional|none
      request:
        body: { <field specs> }
      response:
        success: { status: <code>, body: { <schema> } }
        errors:
          - { status: <code>, condition: "<when>" }

data_flows:
  - name: "<flow name>"
    steps:
      - step: 1
        component: "<component>"
        action: "<what happens>"
        data_in: "<input>"
        data_out: "<output>"

error_handling:
  strategy: "<approach>"
  categories:
    - category: "<error type>"
      status: <code>
      handling: "<how to handle>"

edge_cases:
  - scenario: "<edge case>"
    handling: "<how to handle>"

outputs:
  - .sprint/design.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

See `skills/sprint/templates/design-api.yaml` for the full backend template with all fields.

3. Show checkpoint

---

### Phase 4: Technical Planning (Technical Leadership)

**Goal**: Plan implementation architecture and identify changes.

**Process**:
1. Read all previous phase outputs
2. Analyze codebase for existing patterns:
   - Use Glob to find related files
   - Use Grep to find similar implementations
3. Generate technical spec:

```yaml
# .sprint/technical.yaml
phase: 4
phase_name: technical_planning
role: tech_lead
status: complete
timestamp: <ISO timestamp>
depends_on: design
_schema_version: "1.0"

summary: |
  <1-3 sentence summary of technical approach>

architecture:
  approach: "<How it will be built>"
  patterns:
    - "<Pattern 1>"
    - "<Pattern 2>"
  decisions:
    - decision: "<Architecture decision>"
      rationale: "<Why>"
      alternatives_considered:
        - "<Alternative 1>"

changes:
  new_files:
    - path: "<path/to/new/file>"
      purpose: "<What it does>"
      template: "<existing file to reference>"

  modified_files:
    - path: "<path/to/existing/file>"
      changes:
        - "<Change 1>"
        - "<Change 2>"
      reason: "<Why this file>"

dependencies:
  internal:
    - module: "<existing module>"
      usage: "<how it's used>"
  external:
    - package: "<new package if needed>"
      version: "<version>"
      justification: "<why needed>"

api:
  endpoints:
    - method: GET|POST|PUT|DELETE
      path: "/api/<path>"
      request:
        body: "<schema>"
        params: "<query params>"
      response:
        success: "<success schema>"
        error: "<error schema>"

data:
  models:
    - name: "<Model name>"
      fields:
        - name: "<field>"
          type: "<type>"
          constraints: "<constraints>"
  migrations:
    - "<Migration description>"

risks:
  - risk: "<Risk description>"
    likelihood: high|medium|low
    impact: high|medium|low
    mitigation: "<How to address>"

outputs:
  - .sprint/technical.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

4. Show checkpoint

---

### Phase 5: Sprint Backlog

**Goal**: Create ordered, estimable tasks.

**Process**:
1. Read all previous phase outputs
2. Generate task breakdown:

```yaml
# .sprint/backlog.yaml
phase: 5
phase_name: backlog
role: tech_lead
status: complete
timestamp: <ISO timestamp>
depends_on: technical_planning

summary: |
  <1-3 sentence summary of backlog>

sprint_backlog:
  - id: TASK-001
    title: "<Task title>"
    type: feature|chore|test|docs
    story_ref: US-001
    description: |
      <Detailed description>
    acceptance_criteria:
      - "<Done when...>"
    technical_notes: |
      <Implementation guidance>
    files:
      - "<path/to/file>"
    dependencies:
      blocked_by: []
      blocks: [TASK-002]
    estimate: XS|S|M|L|XL

task_order:
  - TASK-001  # No dependencies
  - TASK-002  # Depends on TASK-001

task_summary:
  total_tasks: <count>
  by_type:
    feature: <count>
    chore: <count>
    test: <count>
  by_estimate:
    XS: <count>
    S: <count>
    M: <count>
    L: <count>
    XL: <count>

outputs:
  - .sprint/backlog.yaml

open_issues: []

signals:
  pass: true
  confidence: high
  blockers: []
```

3. Show checkpoint with task summary

---

### Phases 6-11: Execution through Merge (Delegated)

**Delegated to:** `/orchestrate sprint`

After Phase 5 (Backlog) completes, delegate to the orchestrate command which sequences:

```text
Phase 6:  Implementation (TDD)    → tdd-guide agent
Phase 7:  Code Review (multi)     → code-reviewer, qa-agent
Phase 8:  QA Validation           → qa-agent, verification-loop, e2e-runner
Phase 9:  Security Review         → security-reviewer agent
Phase 10: Pull Request & CI       → gate-decision, push, GitHub CI
Phase 11: PR Review & Merge       → CodeRabbit review loop, merge
```

The orchestrate command reads `.sprint/backlog.yaml` and writes its own handoff files to `.sprint/` as each phase completes. See `commands/orchestrate.md` for details.

---

### Phases 12-13: Post-Merge (Sprint Runner)

These phases run after merge and are managed by the Sprint Runner (not this skill):

- **Phase 12: Monitoring** — Collect real signals (test trends, coverage deltas, error rates)
- **Phase 13: Retrospective** — Analyze sprint, capture learnings, feed back to next intake

See `docs/SPRINT_LIFECYCLE.md` for full details.

---

## State Management

All state is stored in `.sprint/` directory:

```text
.sprint/
├── input.yaml              # Phase 1: Intake
├── product.yaml            # Phase 2: Refinement
├── design.yaml             # Phase 3: Design
├── technical.yaml          # Phase 4: Technical Planning
├── backlog.yaml            # Phase 5: Backlog
├── execution-status.yaml   # Phase 6: Implementation handoff (structured)
├── execution-log.md        # Phase 6: Implementation progress (detailed log)
├── review-code.yaml        # Phase 7: Code Review results
├── qa-report.yaml          # Phase 8: QA results
├── review-security.yaml    # Phase 9: Security Review results
├── ci-report.yaml          # Phase 10: Pull Request & CI results
├── merge-report.yaml       # Phase 11: PR Review & Merge results
├── monitoring-report.yaml  # Phase 12: Post-merge signals
├── retrospective.yaml      # Phase 13a: Sprint analysis
├── feedback-intake.yaml    # Phase 13b: Next sprint intake items
└── sprint-meta.yaml        # Sprint metadata (id, start time, velocity mode, current_phase)
```

### Resume Logic

```text
Read current_phase and velocity_mode from .sprint/sprint-meta.yaml

If velocity_mode == "autonomous":
  If phase 1: Continue input gathering from draft or start fresh
  If phase 2-5: Auto-continue from current_phase
  If phase 6-11: Delegate to orchestrate with current state
  If phase 12-13: Delegate to Sprint Runner

If velocity_mode == "attended":
  If phase 1: Start fresh or continue input gathering
  If phase 2-5: Show previous phase output, ask to continue
  If phase 6-11: Delegate to orchestrate with current state
  If phase 12-13: Delegate to Sprint Runner
```

---

## Validation

Every `.sprint/*.yaml` file MUST include the handoff envelope:

```yaml
phase: <1-13>
phase_name: <name>
role: <role>
status: complete|failed|blocked
timestamp: <ISO 8601>
depends_on: <previous phase_name or null>
_schema_version: "1.0"
summary: |
  <1-3 sentences>
outputs: [...]
open_issues: [...]
signals:
  pass: true|false
  confidence: high|medium|low
  blockers: []
```

### Self-Validation Checklist

Before writing each phase output, verify:

1. All handoff envelope fields are present
2. `phase` matches `phase_name` (e.g., 1 → intake, 2 → refinement, 3 → design, 4 → technical_planning, 5 → backlog)
3. `depends_on` points to the correct previous phase (null for phase 1)
4. `timestamp` is valid ISO 8601
5. Phase-specific body fields are complete
6. If status is "failed" or "blocked", `open_issues` or `signals.blockers` is non-empty

### Python Validation

```bash
python3 -m scripts.sprint.validate .sprint/
```

---

## Checkpoint UX

Checkpoint behavior depends on velocity mode:

### Autonomous Mode (default)

After each stage, output a brief status line and auto-continue:

```text
✓ Phase N: <Phase Name> → .sprint/<file>.yaml
```

No human confirmation. Proceed immediately to the next phase.

### Attended Mode

After each stage, show a detailed summary and ask for confirmation:

```text
┌─────────────────────────────────────────────┐
│ Phase N: <Phase Name> ✓                      │
├─────────────────────────────────────────────┤
│                                             │
│ <Summary of key outputs>                    │
│                                             │
│ Output: .sprint/<phase>.yaml                │
│                                             │
├─────────────────────────────────────────────┤
│ [Continue] [Edit] [Restart Phase]           │
└─────────────────────────────────────────────┘
```

Use AskUserQuestion with options:
- **Continue** - Proceed to next phase
- **Edit** - Open output file for manual edits
- **Restart** - Regenerate this phase's output

---

## Junction Protocol

Phases can be invoked in two modes: **pipeline** (auto-continue through all phases) or **single** (run one phase and return control).

- `/sprint <req>` — **Pipeline mode.** Runs Phases 1-5 sequentially, auto-continuing in autonomous mode.
- `/sprint phase <N>` — **Single mode.** Runs Phase N only, then returns control. No downstream cascade.
- `/sprint-run` — **Full pipeline.** Auto-sequences all 13 phases.
- `/orchestrate sprint` — **Pipeline mode.** Runs Phases 6-11 as a continuous pipeline.
- `/orchestrate phase <N>` — **Single mode.** Runs one execution phase and returns control.

**Once in a pipeline, continue all the way through.** The junction protocol governs single-phase invocation only — use `/sprint phase <N>` or `/orchestrate phase <N>` when you want standalone execution without downstream cascades. This ensures individual phases (TDD, code review, QA, etc.) can be reused in non-sprint workflows.

---

## Single Phase Execution

When invoked via `/sprint phase <N>`, run only the specified phase and return control. This does NOT apply to `/sprint <requirements>`, which runs in pipeline mode (Phases 1-5).

### Prerequisite Check

Before running Phase N, verify that Phase N-1 is complete:

```text
If N == 1:
  No prerequisite. Proceed.
If N > 1:
  Read the Phase N-1 output file from PHASE_FILE_MAP[N-1].
  If file does not exist:
    Halt: "Phase {N-1} ({phase_name}) has not been run.
      Output file .sprint/{filename} not found.
      Run /sprint phase {N-1} first, or /sprint-run for the full lifecycle."
  If file exists:
    Load and check status field.
    If status != "complete":
      Halt: "Phase {N-1} ({phase_name}) is not complete (status: {status}).
        Run /sprint phase {N-1} to complete it first."
    Otherwise: prerequisite satisfied. Proceed.

Phase file map (planning phases 1-5):
  1 → .sprint/input.yaml
  2 → .sprint/product.yaml
  3 → .sprint/design.yaml
  4 → .sprint/technical.yaml
  5 → .sprint/backlog.yaml
```

### sprint-meta.yaml Initialization

```text
If .sprint/sprint-meta.yaml does not exist (standalone invocation):
  Create a minimal sprint-meta.yaml:
    sprint_id: <short uuid>
    _schema_version: "1.0"
    started: <ISO timestamp>
    velocity_mode: autonomous
    requirements: "(standalone phase invocation)"
    current_phase: N
    status: in_progress
    phase_log: []

If sprint-meta.yaml exists:
  Update current_phase to N and status to in_progress.
```

### Execute Phase

Run Phase N exactly as defined in the existing phase sections above.

### Junction Return

After the phase completes:

```text
1. Write phase output file (as specified in the phase section)
2. Update sprint-meta.yaml:
   - current_phase: N + 1 (next phase to run)
   - Append to phase_log
3. Display completion:
   "✓ Phase {N}: {phase_name} complete → .sprint/{filename}
    Ready for Phase {N+1} ({next_phase_name}).
    Run /sprint phase {N+1} to continue, or /sprint-run resume to auto-sequence."
4. STOP. Do not proceed to Phase N+1. Return control to the caller.
```

---

## Example Sessions

### Pipeline Mode (via /sprint or /sprint-run)

```text
User: /sprint Add semantic search to the markets API

Claude: Starting sprint planning (autonomous mode)...
  Scanning codebase for related files...
  Found: src/api/markets.py, src/services/market_service.py, src/rag/embeddings.py

✓ Phase 1: Intake → .sprint/input.yaml
✓ Phase 2: Refinement → .sprint/product.yaml
✓ Phase 3: Design → .sprint/design.yaml
✓ Phase 4: Technical Planning → .sprint/technical.yaml
✓ Phase 5: Backlog → .sprint/backlog.yaml

Planning complete. 4 tasks ready.
```

Pipeline mode auto-continues through all planning phases.

### Single Phase Mode (standalone)

```text
User: /sprint phase 3

Claude: Checking prerequisites...
  ✓ .sprint/product.yaml exists (status: complete)

Running Phase 3 (design)...

✓ Phase 3: Design complete → .sprint/design.yaml
  Ready for Phase 4 (technical_planning).
  Run /sprint phase 4 to continue, or /sprint-run resume to auto-sequence.
```

Control returns to the developer. No downstream cascade.

### Attended Mode

```text
User: /sprint-run attended Add semantic search to the markets API

Claude: Starting sprint planning (attended mode)...

Phase 1: Developer Input
─────────────────────────

I need a few details to build your requirements:

1. What specific search capabilities do you need?
   - Full-text search / Vector/semantic search / Both

2. What's the business driver?

...gathers input via AskUserQuestion...

✓ Phase 1 Complete → .sprint/input.yaml
Continue to Phase 2? [Continue] [Edit] [Restart]
```

---

## Phase Output Validation

After writing each phase output file, validate it against the handoff protocol. Every `.sprint/*.yaml` file **must** include all standard fields.

### Required Fields (all phases)

```text
Handoff Protocol Checklist:
  ✓ phase         — integer (1-13)
  ✓ phase_name    — string (intake|refinement|design|technical_planning|backlog|...)
  ✓ role          — string (developer|product_manager|ux_designer|api_designer|tech_lead|...)
  ✓ status        — enum: complete | failed | blocked | in_progress | draft
  ✓ timestamp     — ISO 8601 format
  ✓ depends_on    — string (previous phase_name) or null for Phase 1
  ✓ summary       — multi-line string, 1-3 sentences
  ✓ outputs       — list of file paths produced
  ✓ open_issues   — list (can be empty)
  ✓ signals.pass  — boolean
  ✓ signals.confidence — enum: high | medium | low
  ✓ signals.blockers   — list (can be empty)
```

### Phase-Specific Required Fields

```text
Phase 1 (intake):     what, why, who
Phase 2 (refinement): epic, user_stories (≥1 with acceptance_criteria), scope
Phase 3 (design):     design_mode, plus:
                        if frontend: ux_requirements.flows, ux_requirements.edge_cases
                        if backend:  api_contract.endpoints, data_flows, error_handling, edge_cases
Phase 4 (technical):  architecture.approach, changes (new_files or modified_files), risks
Phase 5 (backlog):    sprint_backlog (≥1 task with id, title, estimate), task_order, task_summary
```

### Validation Process

After writing each phase file:

1. **Check standard fields** — Verify all 11 handoff protocol fields exist
2. **Check phase-specific fields** — Verify the required fields for that phase exist
3. **Check depends_on chain** — Verify the referenced phase file exists in `.sprint/`
4. **Check enums** — Verify `status`, `confidence`, `priority`, `estimate` values are valid
5. **Report** — If any check fails, show what's missing and fix before proceeding

```text
Validation: .sprint/product.yaml
  ✓ phase: 2
  ✓ phase_name: refinement
  ✓ role: product_manager
  ✓ status: complete
  ✓ timestamp: 2026-02-09T14:30:00Z
  ✓ depends_on: intake → .sprint/input.yaml exists
  ✓ summary: present (2 sentences)
  ✓ outputs: [.sprint/product.yaml]
  ✓ open_issues: [] (empty ok)
  ✓ signals: {pass: true, confidence: high, blockers: []}
  ✓ epic: present
  ✓ user_stories: 3 stories, all have acceptance_criteria
  ✓ scope: in_scope and out_of_scope defined
  All checks passed.
```

---

## Edit Subcommand

**Usage:** `/sprint edit <phase>` (requires explicit invocation — not used in autonomous mode)

Where `<phase>` is a phase number (1-5) or name (intake, refinement, design, technical_planning, backlog).

### Process

```text
1. Parse phase identifier from $ARGUMENTS
   - "edit 1" or "edit intake" → .sprint/input.yaml
   - "edit 2" or "edit refinement" → .sprint/product.yaml
   - "edit 3" or "edit design" → .sprint/design.yaml
   - "edit 4" or "edit technical_planning" or "edit technical" → .sprint/technical.yaml
   - "edit 5" or "edit backlog" → .sprint/backlog.yaml

2. Verify the phase file exists
   - If not: "Phase N has not been completed yet. Run /sprint continue first."

3. Read and display the current contents of the file

4. Ask what the user wants to change (this subcommand is interactive by nature):
   Use AskUserQuestion with options:
   - "Replace a specific field"
   - "Add missing information"
   - "Remove an item"
   - "Show me the file and I'll tell you what to change"

5. Apply the requested changes to the YAML file

6. Re-validate the edited file (see Phase Output Validation)
   - If validation fails: show what's wrong, fix it

7. Check downstream impact:
   - If edited phase < current_phase in sprint-meta.yaml:
     Show: "Phase N was edited but phases N+1 through <current> already exist.
           Downstream phases may be stale."
     Use AskUserQuestion with options:
       - "Re-run downstream phases" → rollback to edited phase + 1, re-execute
       - "Keep downstream as-is" → proceed without changes
       - "Review downstream phases" → show summaries of each downstream phase
```

### Phase Name Mapping

| Input | Phase | File |
|-------|-------|------|
| `1`, `intake` | 1 | `.sprint/input.yaml` |
| `2`, `refinement`, `product` | 2 | `.sprint/product.yaml` |
| `3`, `design` | 3 | `.sprint/design.yaml` |
| `4`, `technical_planning`, `technical` | 4 | `.sprint/technical.yaml` |
| `5`, `backlog` | 5 | `.sprint/backlog.yaml` |

---

## Rollback

**Usage:** `/sprint rollback [phase]` (requires explicit invocation — not used in autonomous mode)

Reverts the sprint to a previous phase by removing all downstream phase outputs.

### Process

```text
1. Parse target phase from $ARGUMENTS
   - "rollback 3" → revert to after Phase 3 (remove Phases 4-5 outputs)
   - "rollback" (no arg) → revert to the phase before current_phase

2. Determine files to remove:
   Phase files by phase number:
     1 → input.yaml
     2 → product.yaml
     3 → design.yaml
     4 → technical.yaml
     5 → backlog.yaml

   Files to remove = all phase files where phase > target_phase

3. Safety check — show what will be removed:
   "Rolling back to Phase 3 (design). This will remove:
     - .sprint/technical.yaml (Phase 4)
     - .sprint/backlog.yaml (Phase 5)

   These files cannot be recovered. Continue?"

   Use AskUserQuestion with options:
     - "Yes, rollback" → proceed
     - "No, cancel" → abort

4. If user confirms:
   a. Delete the identified files using Bash: rm .sprint/<file>
   b. Update .sprint/sprint-meta.yaml:
      - Set current_phase to target_phase
      - Remove rolled-back phases from phases_completed list
   c. Show confirmation:
      "Rolled back to Phase 3 (design).
       Run /sprint continue to resume from Phase 4."

5. If phases 6+ have artifacts (code changes, PRs):
   - BLOCK the rollback
   - "Cannot rollback past Phase 5 — execution phases have produced
     code changes that cannot be automatically reverted.
     Use /sprint reset for a full restart, or fix issues in the
     current phase."
```

### Rollback Limits

- Can only roll back Phases 1-5 (planning phases managed by this skill)
- Phases 6-13 are managed by orchestrate/sprint-run and have side effects (code changes, PRs, merges) that can't be undone by removing YAML files
- To re-run execution phases, use `/sprint-run from <phase>`

---

## Export Issues

**Usage:** `/sprint export-issues`

Creates GitHub issues from the sprint backlog using `gh` CLI.

### Process

```text
1. Verify .sprint/backlog.yaml exists
   - If not: "No backlog found. Run /sprint first to create a backlog."

2. Read .sprint/backlog.yaml and extract sprint_backlog tasks

3. For each task, create a GitHub issue:

   Title: "[TASK-{id}] {title}"

   Body (markdown):
     ## Description
     {description}

     ## Acceptance Criteria
     - [ ] {criterion 1}
     - [ ] {criterion 2}

     ## Technical Notes
     {technical_notes}

     ## Files
     {files list}

     ## Sprint Context
     - **Story:** {story_ref}
     - **Estimate:** {estimate}
     - **Dependencies:** Blocked by {blocked_by}, Blocks {blocks}

     ---
     _Generated from sprint backlog by /sprint export-issues_

   Labels:
     - type:{task_type}  (e.g., type:feature, type:chore, type:test)
     - estimate:{estimate}  (e.g., estimate:M, estimate:S)
     - sprint:{sprint_id from sprint-meta.yaml}

4. Create issues in dependency order (task_order):

   gh issue create --title "[TASK-001] Create database migration" \
     --body "$BODY" \
     --label "type:chore" --label "estimate:S"

5. After creating all issues, link dependencies:
   - For each task with blocked_by, add a comment on the issue:
     "Blocked by #<issue_number> ([TASK-{blocked_by_id}])"

6. Output summary:
   "Created {count} GitHub issues:
     #101 [TASK-001] Create database migration
     #102 [TASK-002] Create NewModel
     #103 [TASK-003] Write unit tests for NewService
     ...

   Labels created: type:feature, type:chore, type:test, estimate:S, estimate:M"

7. Handle duplicates:
   - Before creating, search for existing issues with the same title:
     gh issue list --search "[TASK-{id}]" --json number,title
   - If found: skip and report "Issue already exists: #{number}"
```

### Prerequisites

- `gh` CLI must be authenticated (`gh auth status`)
- Repository must have a GitHub remote

---

## Partial Phase Completion

Phases can be saved in an incomplete state and resumed later.

### Status Values

```text
complete     — Phase fully done, all required fields present, validated
in_progress  — Phase started, some fields populated, not yet validated
draft        — Phase output exists but hasn't been reviewed by user
failed       — Phase attempted but could not complete
blocked      — Phase cannot proceed due to external dependency
```

### How It Works

When a phase is interrupted or the user wants to save progress:

1. **Save as draft** — Write whatever fields have been gathered so far with `status: draft`
2. **Track progress** — Add a `_progress` field to the phase file indicating what's been done:

```yaml
# .sprint/input.yaml (partial)
phase: 1
phase_name: intake
role: developer
status: draft
timestamp: <ISO timestamp>
depends_on: null

summary: null  # Not yet written

what: "Add user authentication"  # Gathered
why: null                         # Not yet gathered
who: null                         # Not yet gathered
constraints: []
context: {}

_progress:
  gathered: [what]
  remaining: [why, who, constraints, context]
  last_question: "why"

outputs:
  - .sprint/input.yaml

open_issues:
  - "Phase incomplete — missing: why, who, constraints, context"

signals:
  pass: false
  confidence: low
  blockers:
    - "Phase not complete"
```

3. **Resume from draft** — When `/sprint continue` is invoked and a phase has `status: draft`:
   - Read the phase file
   - Check `_progress.remaining` for what still needs to be gathered
   - Skip questions that are already answered (fields in `_progress.gathered`)
   - Continue asking for remaining fields
   - When all required fields are gathered, run validation and set `status: complete`

4. **Draft to complete transition:**
   ```text
   Read .sprint/<phase>.yaml
   If status == "draft":
     Check _progress.remaining

     If velocity_mode == "autonomous":
       For each remaining field:
         Infer value from $ARGUMENTS, codebase context, and prior phase outputs
         Write field to file
         Move field from remaining to gathered

     If velocity_mode == "attended":
       For each remaining field:
         Ask user for input via AskUserQuestion
         Write field to file
         Move field from remaining to gathered

     When remaining is empty:
       Remove _progress field
       Set status: complete
       Run validation
   ```

5. **Downstream blocking** — A phase with `status: draft` blocks the next phase:
   ```text
   Before starting Phase N:
     Read .sprint/<phase_N-1>.yaml
     If status != "complete":
       "Phase N-1 ({phase_name}) is not complete (status: {status}).
        Run /sprint continue to finish it first."
   ```

### Progress Fields Per Phase

```text
Phase 1: gathered/remaining from [what, why, who, constraints, context]
Phase 2: gathered/remaining from [epic, user_stories, success_metrics, scope]
Phase 3: gathered/remaining from [design_mode, flows/api_contract, edge_cases]
Phase 4: gathered/remaining from [architecture, changes, dependencies, risks]
Phase 5: gathered/remaining from [sprint_backlog, task_order, task_summary]
```

---

## Known Limitations

- No concurrent sprint support (single .sprint/ dir)
- Phases 12-13 handled by Sprint Runner (`commands/sprint-run.md`)
- No integration with external project management tools (except GitHub issues via export-issues)
- Rollback limited to planning phases (1-5); execution phases have side effects

**Open work items:** `docs/SPRINT_BACKLOG.md`
**Architecture decisions:** `docs/planning/TECHNICAL_DECISIONS.md` (Decisions 5-9)
**Testing and contributing:** `skills/sprint/README.md`
