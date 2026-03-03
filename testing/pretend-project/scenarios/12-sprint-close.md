# Scenario 12: Sprint Close and Learning

## Features Exercised

- Commands: `/collect-signals`, `/learn`, `/tree reset`, `/tree reset --all`,
  `/tree closedone`
- Skills: sprint-retrospective, feedback-synthesizer, learned
- Hooks: recap-on-stop (auto)

## Prerequisites

Scenarios 04-11 completed (features implemented, PRs merged or ready).

## Prompts

### Prompt 12-A: Collect Post-Merge Signals

```text
The auth PR was merged. Collect signals from CI/CD, monitoring, and any
feedback channels.

Use /collect-signals.
```

**What Should Happen:**
- Claude invokes `/collect-signals` which:
  - Checks CI results post-merge
  - Looks for deployment status (if configured)
  - Checks for any reported issues
  - Gathers metrics (test count, coverage delta, build time)
- The feedback-synthesizer skill transforms raw signals into actionable
  intake items.

**Checkpoint:** Signal report with: CI status, coverage change, any new
issues. Synthesized into actionable items for next sprint.

---

### Prompt 12-B: Sprint Retrospective

```text
Let's do a retrospective on this sprint. What went well? What didn't? What
should we change?

Use /sprint-retrospective.
```

**What Should Happen:**
- Claude invokes `/sprint-retrospective` which uses the sprint-retrospective
  skill.
- Analyzes the sprint:
  - What was planned vs what was delivered
  - Velocity metrics (stories completed, code written, tests added)
  - Pain points (any rework, blocked items, slow reviews)
  - Process improvements
- Structures findings as: keep doing, start doing, stop doing.

**Checkpoint:** Retrospective document with concrete insights. At least one
actionable improvement per category.

---

### Prompt 12-C: Extract Learned Patterns

```text
What reusable patterns did we establish during this sprint? Save them for
future reference.

Use /learn.
```

**What Should Happen:**
- Claude invokes `/learn` which triggers the learned skill.
- Extracts patterns:
  - Auth implementation pattern (JWT + Flask)
  - Service layer pattern
  - Test naming conventions used
  - TDD workflow that worked
  - Code review process
- Saves to a learned patterns file.

**Checkpoint:** Patterns documented in a persistent location. Can be
referenced in future sessions via the learned skill.

---

### Prompt 12-D: Reset Completed Worktree

```text
The auth feature is merged. Do a full reset of the auth worktree.

Use /tree reset.
```

**What Should Happen:**
- Claude invokes `/tree reset` which runs the 6-phase reset:
  1. Ship: ensure all changes are committed and pushed
  2. AI wrapup: generate a session summary
  3. Learning extraction: save any patterns
  4. Branch cleanup: delete the feature branch
  5. Worktree removal: remove the worktree directory
  6. State cleanup: update worktree tracking
- Each phase runs in order with status reporting.

**Checkpoint:** Auth worktree removed. Branch deleted locally and remotely.
Session summary saved. `git worktree list` no longer shows the auth worktree.

---

### Prompt 12-E: Batch Reset All Worktrees

```text
Sprint is done. Reset all remaining worktrees.

/tree reset --all
```

**What Should Happen:**
- Claude invokes `/tree reset --all` which:
  - Lists all active worktrees
  - Runs the 6-phase reset for each one
  - Reports progress for each worktree
- If any worktrees have uncommitted changes, it warns before proceeding
  (unless --force is used).

**Checkpoint:** All worktrees removed. Only the main working directory remains.

---

### Prompt 12-F: Close All Done Worktrees

```text
/tree closedone
```

**What Should Happen:**
- Removes all worktrees that have been fully merged/completed.
- Leaves any WIP worktrees intact.

**Checkpoint:** Only active/WIP worktrees remain.

---

### Prompt 12-G: Session Recap (Hook Test)

When the session ends (or you run `/stop`), the recap-on-stop hook should:
- Recap the original query
- Summarize what was accomplished
- Note any outstanding items

**Checkpoint:** Recap output appears at session end.
