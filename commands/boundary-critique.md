---
description: Challenge problem framing assumptions (Critical Systems Heuristics)
help-usage: '`/boundary-critique <problem statement or topic>`'
---

# Boundary Critique

Structured interrogation of a problem definition using Critical Systems
Heuristics (CSH). Surfaces hidden assumptions, power structures, value
judgments, and excluded perspectives in how a problem is framed.

**This is not a problem-solving tool. It is a problem-questioning tool.**

## Usage

```
/boundary-critique <problem statement or topic>
```

## When to Use

- A problem statement exists but the team suspects it may be misframed
- Conflicting stakeholder perspectives need to be surfaced
- Before committing to a solution direction on a complex or ambiguous problem
- When prior attempts to solve a problem have failed

## Process

```text
/boundary-critique "We need to migrate to microservices"
    │
    ├─► Step 1: State the problem as given
    │
    ├─► Step 2: Apply 12 boundary questions
    │   ├─► Motivation (Q1-Q3): Purpose, client, success measures
    │   ├─► Control (Q4-Q6): Decision-maker, resources, environment
    │   ├─► Knowledge (Q7-Q9): Expert, expertise type, limits
    │   └─► Legitimation (Q10-Q12): Witness, emancipated, worldview
    │
    ├─► Step 3: Analyze gaps between Involved and Affected perspectives
    │
    └─► Step 4: Reframe the problem
            → Original vs. reframed statement
            → Changes traced to specific boundary findings
            → Sacrificed concerns acknowledged
```

## Output

- Boundary analysis across all 12 CSH questions
- Gap analysis with critical conflicts ranked by severity
- Reframed problem statement with explicit boundary judgments
- Acknowledged limitations of the reframing

## Integration

Use alongside other problem-definition tools:
- Use `/problem-definition` for structured problem exploration
- Use `/requirements-engineering` to formalize the (re)framed problem

Uses the **boundary-critique** skill internally.
