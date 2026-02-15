# Sprint Runner

Run the full 13-phase sprint lifecycle autonomously. The developer provides requirements once; everything else runs without human intervention.

**Lifecycle reference:** `docs/SPRINT_LIFECYCLE.md`

## Usage

```
/sprint-run [mode] <requirements>
```

- `/sprint-run Add user authentication` — Start autonomous sprint (default)
- `/sprint-run attended Add user authentication` — Start with human checkpoints
- `/sprint-run resume` — Resume from last completed phase
- `/sprint-run status` — Show sprint progress
- `/sprint-run from <phase> <requirements>` — Start or restart from a specific phase

## Instructions

**You are running a full automated sprint.** Sequence all 13 phases, manage state in `.sprint/`, and handle failures according to the velocity mode.

### 1. Initialize Sprint

Create the `.sprint/` directory and metadata:

```yaml
# .sprint/sprint-meta.yaml
sprint_id: <short uuid>
_schema_version: "1.0"
started: <ISO timestamp>
velocity_mode: autonomous|attended
requirements: |
  <developer's original input>
current_phase: 1
status: in_progress
phase_log:
  - phase: 1
    phase_name: intake
    status: complete
    started_at: <ISO timestamp>
    completed_at: <ISO timestamp>
    output_file: input.yaml
    validated: true
phases_failed: []
retry_count: 0
revision_cycles: 0
last_error: null
```

`phase_log` replaces `phases_completed`. Each entry records timing, output file, and validation status — enabling duration analysis in the retrospective.

If `.sprint/` already exists and `$ARGUMENTS` is not `resume`:
- In autonomous mode: auto-resume from `current_phase` in `sprint-meta.yaml`
- In attended mode: warn the developer and ask whether to resume or reset

### Feedback Carry-Forward

When starting a new sprint (not resuming), check for feedback from a previous sprint:

```text
If .sprint/feedback-intake.yaml exists from a previous sprint:
  The sprint skill handles this in Phase 1 (see skills/sprint/SKILL.md).

  In autonomous mode: automatically include critical items only. Skip high/medium/low.
  In attended mode: surface critical and high items. Let developer choose which to include.
```

Sprints are never auto-started from feedback. The developer always explicitly invokes `/sprint-run` or `/sprint`. Feedback items are surfaced as suggestions, not triggers.

### 2. Phase Sequencing

Execute phases in order. Each phase reads the previous handoff, does its work, and writes its own handoff to `.sprint/`.

```
Phase 1-5:   Delegate to /sprint skill (planning)
Phase 6-11:  Delegate to /orchestrate sprint (execution)
Phase 12:    Delegate to /collect-signals (monitoring)
Phase 13:    Apply sprint-retrospective skill, then feedback-synthesizer skill
```

After each phase completes:
1. Update `current_phase` and append to `phase_log` in `.sprint/sprint-meta.yaml`
2. In attended mode: show phase summary and ask to continue

### 3. Phase 1-5: Planning

**Phase 1 always runs via the sprint skill** (human intake):

```
/sprint <requirements>    # Phases 1-5: pipeline mode (auto-continues through all planning phases)
```

**Phases 2-5 branch based on team_mode:**

```text
If team_mode is enabled (sprint-meta.yaml team_mode: true, or /sprint-run team <req>):
  Invoke /plan-swarm [attended]
  — Parallelizes research across Context Agent, Researcher, Technical Scout, Product Analyst
  — Produces identical handoff files to sequential mode
  — See commands/plan-swarm.md

Otherwise (default):
  Continue with /sprint <requirements>
  — Sequential Phases 1-5 via sprint skill (pipeline mode)
```

The sprint skill handles (in both modes):
- Phase 1: Intake — gather what/why/who/constraints
- Phase 2: Refinement — user stories, acceptance criteria
- Phase 3: Design — UX flows or API contracts
- Phase 4: Technical Planning — architecture, file changes, risks
- Phase 5: Backlog — ordered task list with estimates

**Note:** Individual phases can also be invoked standalone via `/sprint phase <N>` (single mode — returns control after that phase). Pipeline mode (`/sprint <req>`) auto-continues through all 5 phases.

**On completion:** `.sprint/backlog.yaml` exists with ordered tasks.

### 4. Phase 6-11: Execution

Invoke the orchestrate command in continuous mode:

```
/orchestrate sprint
```

The orchestrate command runs Phases 6-11 as a continuous pipeline:
- Phase 6: Implementation (TDD) — `tdd-guide` agent per task
- Phase 6.5: Test Swarm (optional) — parallel test writers when coverage < 70% or 5+ tasks
- Phase 7+9: Review Swarm — `code-reviewer` + `qa-agent` + `security-reviewer` as Agent Team
- Phase 8: QA Validation — `verification-loop` skill (lint, format, type check, tests, coverage), `e2e-runner`
- Phase 10: Pull Request & CI — Gate Decision skill (reads Phase 7+9 and 8 outputs) → `push` command → GitHub CI
- Phase 11: PR Review & Merge — CodeRabbit review loop → resolve merge conflicts → merge PR

**Pause sentinel:** Even in continuous mode, sprint-run adds junction awareness. After each sub-phase completes within `/orchestrate sprint`:
1. Read `.sprint/sprint-meta.yaml` for `current_phase`
2. If `.sprint/pause` exists: halt and report "Sprint paused at Phase {N}. Remove `.sprint/pause` and run `/sprint-run resume` to continue."
3. In attended mode: show phase completion checkpoint
4. In autonomous mode: continue (no checkpoint)

**On completion:** Code is merged. `.sprint/merge-report.yaml` exists. All phase handoffs follow the standard handoff protocol.

### 5. Phase 12: Monitoring

Invoke the signal collector command:

```
/collect-signals
```

Collects real post-merge signals: build status, test trends, coverage deltas, dependency health.

**On completion:** `.sprint/monitoring-report.yaml` exists with real data.

### 6. Phase 13: Retrospective

Apply two skills in sequence:

**First — Sprint Retrospective skill:**
Read all `.sprint/*.yaml` files. Analyze what worked, what didn't, review effectiveness, estimation accuracy, pattern extraction. Write `.sprint/retrospective.yaml`.

**Then — Skill Extraction (if applicable):**
Read `.sprint/retrospective.yaml` and check `patterns_extracted` for items with `save_as_skill: true`.

```text
For each pattern with save_as_skill: true:
  1. Present the pattern to the developer:
     "The retrospective identified a reusable pattern:

      Name: <pattern.name>
      Context: <pattern.context>
      Description: <pattern.description>

      Save this as a skill?"

  2. In attended mode: Use AskUserQuestion with options:
       - "Yes, create skill" → invoke skill-creator with the pattern details
       - "Skip" → do not create skill

     In autonomous mode: skip skill extraction entirely (no human to confirm).

  3. If approved:
     - Create skill file at .claude/skills/learned/<suggested_name>/SKILL.md
     - Use the pattern's description as the skill's core content
     - Use skill_metadata.category and triggers for the skill's frontmatter
     - Log the creation in sprint-meta.yaml under skills_created: []
```

Skill extraction is interactive and only runs in attended mode. In autonomous mode, this step is skipped entirely.

**Then — Feedback Synthesizer skill:**
Read `.sprint/monitoring-report.yaml` and `.sprint/retrospective.yaml`. Transform signals and insights into actionable intake items. Write `.sprint/feedback-intake.yaml`.

### 7. Sprint Summary

After Phase 13, produce a final summary:

```
SPRINT COMPLETE
===============
Sprint: <sprint_id>
Duration: <hours>
Mode: autonomous|attended

TASK SUMMARY
────────────
Planned: <count>
Completed: <count>
Deferred: <count>

QUALITY
───────
Tests: <pass/fail>
Coverage: <percentage> (delta: <+/->)
Reviews: <pass/fail>
Security: <pass/fail>

HEALTH
──────
Overall: healthy|warning|degraded

FEEDBACK ITEMS
──────────────
<count> items generated for next sprint
See: .sprint/feedback-intake.yaml

ARTIFACTS
─────────
.sprint/ directory contains all phase handoffs.
```

## Failure Handling

### Autonomous Mode

When a phase fails:

1. **Classify the failure:**
   - Retriable (test flake, transient CI failure) → retry once
   - Fixable (review feedback, lint errors) → attempt auto-remediation, re-run phase
   - Blocking (build failure, critical security issue) → halt

2. **On retry failure or blocking issue:**
   - Write failure details to `.sprint/sprint-meta.yaml`
   - Set `status: blocked`
   - Produce a partial sprint report explaining what succeeded and what failed
   - Suggest manual intervention steps

3. **Revision cycle (Phase 10):**
   - If Gate Decision returns `REVISE`, loop back to Phase 6 with review findings
   - Maximum 2 revision cycles allowed (3 total attempts: initial + 2 cycles)
   - On the 3rd `REVISE` verdict, escalate to BLOCKED
   - Track `revision_cycles` count in `sprint-meta.yaml`

### Attended Mode

When a phase fails:
- Show the failure details
- Ask the developer: Fix and retry / Skip this phase / Halt sprint

## Resume Logic

When `/sprint-run resume` is invoked:

1. Read `.sprint/sprint-meta.yaml` (contains `current_phase`, `phase_log`, `velocity_mode`)
2. Verify the last completed phase's handoff file exists
3. Resume from `current_phase`
4. If the last phase failed:
   - In autonomous mode: retry once, then halt with report
   - In attended mode: offer the developer: retry / skip / halt

## Multi-Session Handling

A full 13-phase sprint will exceed a single context window. The sprint is designed to survive session boundaries using file-based state.

### How It Works

All sprint state lives in `.sprint/*.yaml` files on disk. No state is held in memory. This means:

- **Any session can resume** by reading `.sprint/sprint-meta.yaml` to find `current_phase`
- **Phase handoffs are durable** — each phase reads the previous phase's YAML file, not in-memory data
- **`/sprint-run resume` works across sessions** — it picks up exactly where the last session left off

### Context Compaction on Resume

When resuming in a new session, build context efficiently:

```text
1. Read .sprint/sprint-meta.yaml for current state
2. For each completed phase, read ONLY the summary field from its handoff file
   (not the full contents — summaries are 1-3 sentences by design)
3. Read the FULL contents of:
   - The last completed phase's handoff (immediate context)
   - The current phase's handoff if it exists (may be in_progress/draft)
4. Proceed with current_phase
```

This gives the agent enough context to continue without re-reading every phase in detail.

### Session Boundary Checkpoints

The sprint naturally checkpoints at phase boundaries. When a phase completes:

1. Phase handoff file is written to disk (durable)
2. `sprint-meta.yaml` is updated with new `current_phase` (durable)
3. If the session ends here, the next session resumes from the next phase

No mid-phase checkpointing is needed — the sprint skill's partial completion support (draft/in_progress status) handles interrupted phases within a single session. If a session ends mid-phase, resume will detect the draft status and continue gathering remaining fields.

## Arguments

$ARGUMENTS:
- `<requirements>` — Start autonomous sprint with these requirements
- `attended <requirements>` — Start attended sprint
- `team <requirements>` — Start sprint with team_mode enabled (parallel planning + Agent Team reviews)
- `resume` — Resume from last completed phase
- `status` — Show current sprint state
- `from <N> <requirements>` — Start or re-run from phase N (e.g., `from 7` to re-run reviews)

## Rollback

Rollback is not a standalone subcommand. It is triggered by the **smart router** — when bare `/sprint` shows a blocked/failed phase, one option is "Roll back to Phase N". Rollback deletes output files for phases after the target and resets `current_phase` in sprint-meta.yaml.

**Note:** Revision cycles do not use rollback. On a REVISE verdict, the orchestrate command iterates — it re-runs Phases 6-11 with findings carried forward, overwriting each phase's output. Prior outputs remain available as context.

**Validation:** `python3 -m scripts.sprint.validate .sprint/` can verify the sprint directory is in a valid state after rollback.

## Composition

This command delegates to:
- `skills/sprint/` — Phase 1 (intake, always) + Phases 2-5 (planning, when team_mode off)
- `commands/plan-swarm.md` — Phases 2-5 (planning, when team_mode on)
- `commands/orchestrate.md` — Phases 6-11 (execution, includes review-swarm and optional test-swarm)
- `commands/collect-signals.md` — Phase 12 (monitoring)
- `skills/sprint-retrospective/` — Phase 13a (analysis)
- `skills/feedback-synthesizer/` — Phase 13b (intake generation)

## Used By

This is the top-level entry point. Not called by other commands.
