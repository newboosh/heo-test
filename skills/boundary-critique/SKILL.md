---
name: boundary-critique
description: Critical Systems Heuristics (CSH) boundary analysis for problem definition. Use ONLY when explicitly invoked by a user or agent to interrogate whether the right problem is being solved.
argument-hint: [problem-statement or topic]
model: opus
disable-model-invocation: true
---

# Boundary Critique (Critical Systems Heuristics)

Structured interrogation of a problem definition using Werner Ulrich's Critical Systems Heuristics (CSH). This skill surfaces the hidden assumptions, power structures, value judgments, and excluded perspectives embedded in how a problem is framed.

**This is not a problem-solving tool. It is a problem-questioning tool.**

## When to Use

- An agent or user explicitly requests boundary critique
- A problem statement exists but the team suspects it may be misframed
- Conflicting stakeholder perspectives need to be surfaced before requirements work begins
- Before committing to a solution direction on a complex or ambiguous problem

## Do NOT Auto-Invoke

This skill consumes significant context and produces discomfort by design. It should never run automatically. It is consumed only by explicit invocation: `/boundary-critique [problem-statement]`.

## Theoretical Foundation

**Source**: Werner Ulrich, *Critical Heuristics of Social Planning* (1983)
**Tradition**: Critical Systems Thinking
**Core principle**: Every problem definition is partial and serves someone's interests. The way we draw boundaries around "the problem" determines who gets a say, what counts as evidence, and what success looks like. These boundary judgments are normative (value-based), not neutral.

**How this helps define the problem**: By forcing explicit examination of what's included and excluded from the problem frame, CSH prevents the team from solving a well-defined version of the wrong problem.

## Process

### Step 1: State the Problem as Given

Record the problem statement exactly as received. Do not interpret or improve it.

```text
Problem as stated: $ARGUMENTS
```

**How this helps define the problem**: Capturing the initial framing creates a baseline. The gap between the initial statement and the post-critique reframing IS the value of this process.

### Step 2: Apply the 12 Boundary Questions

For each question below, answer from TWO perspectives:
- **Involved** ("is"): Those designing, deciding, or funding
- **Affected** ("ought"): Those impacted but lacking decision power

Present each answer pair as a row. Flag conflicts between the two columns.

#### Category 1: MOTIVATION — What is the purpose?

| # | Question | How This Helps Define the Problem |
|---|----------|----------------------------------|
| 1 | **Who is the client?** Whose interests does this problem definition actually serve? | Reveals whether the stated beneficiary and the actual beneficiary are the same person. Misalignment here means the problem is framed for the wrong audience. |
| 2 | **What is the purpose?** What are the intended consequences of solving this problem? | Forces articulation of what "solved" means. Vague purposes produce vague problems. |
| 3 | **What is the measure of success?** How will we know the problem is actually solved? | Prevents the problem from being defined in untestable terms. If success can't be measured, the problem isn't defined. |

**Output format for each question:**

```markdown
### Q1: Who is the client?

| Perspective | Answer |
|-------------|--------|
| **Involved** (designers/sponsors) | [Who they say the client is] |
| **Affected** (impacted parties) | [Who the affected believe the client should be] |

**Conflict?** [Yes/No — describe the gap]
**Implication for problem definition:** [How this changes what the problem actually is]
```

#### Category 2: CONTROL — What is the power structure?

| # | Question | How This Helps Define the Problem |
|---|----------|----------------------------------|
| 4 | **Who is the decision-maker?** Who can change the measures of success? | Identifies who actually controls the problem frame. The problem may be defined to fit the decision-maker's constraints rather than the actual need. |
| 5 | **What resources are controlled?** What conditions are under the decision-maker's control? | Reveals whether the problem is scoped by what's real or by what's convenient. Resource boundaries often silently reshape the problem. |
| 6 | **What is the decision environment?** What conditions matter but aren't controlled? | Surfaces the constraints that the problem definition ignores. These uncontrolled factors are often where the real problem lives. |

#### Category 3: KNOWLEDGE — What informs the plan?

| # | Question | How This Helps Define the Problem |
|---|----------|----------------------------------|
| 7 | **Who is the expert?** Whose knowledge counts as valid? | Reveals what kind of problem this is implicitly assumed to be. If only technical experts are consulted, the problem is assumed to be technical — which may be wrong. |
| 8 | **What expertise is relied upon?** What type of knowledge is being used? (Scientific, experiential, local, institutional) | Exposes blind spots. Problems defined only through one type of knowledge miss dimensions that other types would reveal. |
| 9 | **What guarantees the expertise?** What are the limits of the relied-upon knowledge? | Identifies where the problem definition is standing on uncertain ground. No expertise is universal. |

#### Category 4: LEGITIMATION — Who bears the consequences?

| # | Question | How This Helps Define the Problem |
|---|----------|----------------------------------|
| 10 | **Who is the witness?** Whose views are considered relevant to evaluating the outcome? | Reveals who is excluded from defining success. The excluded parties often experience the problem most acutely. |
| 11 | **Who is emancipated?** Who is protected from side effects? Who is not? | Surfaces sacrificed concerns — the costs that the problem definition renders invisible. |
| 12 | **What worldview underlies this?** What values, beliefs, and assumptions are taken for granted? | The deepest question. The worldview determines what counts as a problem in the first place. Changing the worldview changes the problem. |

### Step 3: Analyze the Gaps

After completing all 12 questions:

1. **List every conflict** between the Involved and Affected columns
2. **Rank conflicts by severity**: Which gaps most distort the problem definition?
3. **Identify sacrificed concerns**: What legitimate needs are rendered invisible by the current framing?
4. **Name the dominant worldview**: What unstated belief system is shaping the problem boundary?

**How this helps define the problem**: The conflicts ARE the problem definition work. Each gap between "involved" and "affected" perspectives represents a boundary judgment that needs to be made explicitly, not left hidden.

### Step 4: Reframe the Problem

Using the gap analysis, produce:

1. **Original problem statement** (from Step 1)
2. **Reframed problem statement** that accounts for the most significant boundary conflicts
3. **What changed and why** — trace each change to a specific boundary question finding
4. **Sacrificed concerns acknowledged** — what the reframed problem still doesn't address, stated explicitly
5. **Boundary judgments made explicit** — the choices that were previously hidden, now named

**How this helps define the problem**: The reframed problem is more honest. It names its own limitations. This prevents downstream requirements from being built on a foundation of unexamined assumptions.

## Output Format

```markdown
# Boundary Critique: [Problem Topic]

**Date:** [timestamp]
**Problem as stated:** [original statement]
**Source:** [who provided the problem statement]

## Boundary Analysis

### Motivation (Purpose)
[Q1-Q3 with Involved/Affected answers and conflict flags]

### Control (Power)
[Q4-Q6 with Involved/Affected answers and conflict flags]

### Knowledge (Expertise)
[Q7-Q9 with Involved/Affected answers and conflict flags]

### Legitimation (Consequences)
[Q10-Q12 with Involved/Affected answers and conflict flags]

## Gap Analysis

### Critical Conflicts
1. [Most severe gap — description and implication]
2. [Second most severe]
...

### Sacrificed Concerns
- [Concern 1: who bears it, why it's excluded]
- [Concern 2: ...]

### Dominant Worldview
[Named worldview and its effect on problem framing]

## Reframed Problem

**Original:** [statement]
**Reframed:** [statement]

### What Changed
| Change | Traced to Question | Finding |
|--------|-------------------|---------|
| [change 1] | Q[n] | [specific finding] |

### Acknowledged Limitations
- [What this reframing still doesn't address]

## Provenance
- **Method:** Critical Systems Heuristics (Ulrich, 1983)
- **Tradition:** Critical Systems Thinking
- **Applied by:** [agent/user]
- **Status:** Working document — subject to revision as understanding deepens
```

## What This Skill Does NOT Do

- It does not generate solutions
- It does not seek consensus — it surfaces conflict
- It does not replace domain expertise — it questions which expertise is being privileged


## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `problem-definition` | Complementary. Boundary critique enriches problem definition by surfacing hidden assumptions and excluded perspectives. Can be invoked before or after `/problem-definition`. |
| `requirements-engineering` | Independent. Boundary critique operates at the problem framing level, upstream of requirements specification. |

## References

- Ulrich, W. (1983). *Critical Heuristics of Social Planning*. Haupt.
- Ulrich, W. (2005). "A Brief Introduction to Critical Systems Heuristics (CSH)." ECOSENSUS project website.
- Rittel, H. & Webber, M. (1973). "Dilemmas in a General Theory of Planning." *Policy Sciences*, 4(2).
- Churchman, C.W. (1968). *The Systems Approach*. Delacorte Press.
