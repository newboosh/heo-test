---
description: Define the problem before solving it
help-usage: '`/problem-definition <situation or problem description>`'
---

# Problem Definition

Structured problem exploration and framing before any requirements or solution
work begins. Answers the question: **"What is the actual problem?"**

## Usage

```
/problem-definition <situation or problem description>
```

## When to Use

- Before `/requirements-engineering` when the problem isn't yet clear
- When a user says "I want to build X" but hasn't articulated why or for whom
- When multiple stakeholders disagree on what the problem is
- When a proposed solution exists but the underlying problem hasn't been stated

## Process

```text
/problem-definition "Users are complaining about slow search"
    │
    ├─► Step 1: Explore the Problem Situation
    │       → Context, concerns, interconnections, prior attempts
    │
    ├─► Step 2: Classify the Problem
    │       → Tame / Complicated / Wicked / Mess
    │
    ├─► Step 3: Frame the Problem
    │       → Current frame, alternatives, selected frame
    │
    ├─► Step 4: Identify Who Has the Problem
    │       → Problem owners, how they experience it, cost
    │
    ├─► Step 5: Define the Gap
    │       → IS/IS-NOT analysis, problem statement, worth solving?
    │
    └─► Step 6: Characterize the Solution Space
            → Feasible classes, exclusions, trade-offs
            → Recommended next step: /requirements-engineering
```

## Output

Written to `.problem-definition/`:

- `problem-definition.md` — human-readable document
- `handoff.yaml` — structured contract for downstream skills

## Integration

After problem definition:
- Use `/requirements-engineering` to formalize into specifications
- Use `/boundary-critique` to challenge framing assumptions

Uses the **problem-definition** skill internally.
