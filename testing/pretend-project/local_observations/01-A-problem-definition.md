# Observation: Prompt 01-A — Define the Problem

**Scenario:** `01-planning-and-requirements.md` → Prompt 01-A
**Date:** 2026-03-03

## Prompt Given

```text
I need to build a collaborative task management API. Before we start coding,
help me define the problem clearly. What are we actually solving? Who are the
users? What are the constraints?

Use /problem-definition to think this through.
```

Then retried with:
```text
Use /heo-test:problem-definition to think this through
```

## Expected Behavior (from scenario)

1. Claude invokes the `problem-definition` skill.
2. It produces a structured problem statement covering: user personas, core problem, constraints, success criteria, out-of-scope items.
3. The `boundary-critique` skill may be referenced to challenge assumptions.
4. **Checkpoint:** A problem definition document is produced. It identifies at least: API consumers (frontend app, mobile), admin users, team leads. It flags constraints like auth requirements, multi-tenancy, and rate limits.

## Actual Behavior

### First Attempt (natural language `/problem-definition`)

- Agent correctly identified that `/problem-definition` doesn't exist as a skill.
- Suggested `/task` as an alternative (its Phase 1 is Discovery, which covers problem definition).
- Asked the user's preference — good fallback behavior.

### Second Attempt (explicit `/heo-test:problem-definition`)

- Agent again correctly identified the skill doesn't exist.
- Offered two alternatives: `/task` (Phase 1 Discovery) and `/plan`.
- Recommended `/task` as the better fit for problem definition work.
- Asked user preference — consistent, helpful fallback.

### Issues

1. **`/problem-definition` skill does not exist** — The scenario references a skill that isn't in the plugin. This is a **scenario spec bug**, not a plugin behavior bug. The scenario lists `problem-definition` in Features Exercised, but the skill hasn't been built.
2. **Agent handled the missing skill gracefully** — Both attempts got clear, helpful responses explaining the skill doesn't exist and offering alternatives. This is good error handling.
3. **No problem definition document produced** — Since the skill doesn't exist, no structured output was generated. The checkpoint cannot be evaluated.

### Severity Assessment

| Issue | Severity | Notes |
|-------|----------|-------|
| `problem-definition` skill doesn't exist | **HIGH (scenario bug)** | Scenario references an unbuilt skill |
| Agent fallback behavior | **Good** | Correctly identified missing skill, offered alternatives |
| No checkpoint met | N/A | Can't evaluate — skill doesn't exist |

### Checkpoint Evaluation

- **Problem definition document produced?** — NO (skill doesn't exist)
- **Identifies API consumers, admin users, team leads?** — NOT TESTED
- **Flags auth, multi-tenancy, rate limits constraints?** — NOT TESTED

## Recommendations

1. **Either build the `problem-definition` skill or update the scenario** to use `/task` Phase 1 instead. The scenario currently references skills that don't exist: `problem-definition`, `requirements-engineering`, `boundary-critique`.
2. The agent's fallback to suggest `/task` is actually the right answer — consider whether a dedicated `problem-definition` skill is needed or if `/task` Phase 1 covers it.
3. Check which other skills in scenario 01's "Features Exercised" list actually exist: `plan-context`, `problem-definition`, `requirements-engineering`, `boundary-critique`, `standards-lookup`.
