# Sprint Runner

**Phase position:** Wraps all 13 phases
**Priority:** Critical
**Status:** Not in development

## Purpose

Top-level orchestrator that sequences the entire sprint lifecycle end-to-end. The "main loop." The developer invokes this once with their requirements; everything else is autonomous.

## Inputs

- Developer requirements (natural language or structured YAML)
- Velocity mode: `autonomous` (default) or `attended`
- Optional: previous sprint's retrospective (for continuity)

## Outputs

- Completed `.sprint/` directory with all 13 phase handoffs
- Final sprint summary report
- (If feedback loop) new intake items for next sprint

## Responsibilities

1. Initialize `.sprint/` directory and `sprint-meta.yaml`
2. Run Phases 1-5 via `skills/sprint/` (planning)
3. Delegate Phases 6-11 to `/orchestrate sprint` (execution)
4. Run Phase 12 via Post-Merge Signal Collector (monitoring)
5. Run Phase 13 via Sprint Retrospective Runner (retrospective)
6. Handle phase failures:
   - **Autonomous mode:** Attempt remediation, retry once, then halt with report
   - **Attended mode:** Pause and ask developer for guidance
7. Track overall sprint state in `.sprint/.current-phase`

## Velocity Modes

### Autonomous (default)
- No human checkpoints
- Phases run end-to-end
- Failures trigger automatic remediation or halt with report
- Carried forward from retired `task.md` `go` template

### Attended
- Human checkpoint after each phase
- Phase output shown, developer approves before continuing
- For high-risk or exploratory work
- Carried forward from retired `task.md` `slow` template

## Composition Patterns Used

- **Pipeline:** Phases 1-13 sequentially
- **Delegation:** Phases 1-5 to sprint skill, Phases 6-11 to orchestrate
- **Gate:** Gate Decision between QA and Merge
- **Loop:** Full cycle is a loop (Phase 13 → Phase 1)
- **Decorator:** Each phase wrapped with handoff protocol (read prev, write own)

## Open Questions (Resolved)

- ~~Should the Sprint Runner be a command (`/sprint-run`) or extend the existing `/sprint` command?~~ → Separate command `/sprint-run`. Sprint skill handles planning (1-5), sprint-run wraps all 13.
- ~~How does it handle multi-session sprints (context window limits)?~~ → Phase-level resume via `sprint-meta.yaml`. Context compaction on resume reads only summaries of completed phases. See "Multi-Session Handling" in `commands/sprint-run.md`.
- ~~Should it support partial re-runs (e.g., re-run only Phases 7-11 after fixing review feedback)?~~ → Yes, via `/sprint-run from <phase>`.
