---
name: requirements-engineering
description: Formal requirements elicitation, specification, and validation following IEEE 29148:2018. Use ONLY when explicitly invoked. Expects a defined problem (from /problem-definition or user-provided).
argument-hint: [problem-statement or feature-name]
model: opus
disable-model-invocation: true
---

# Requirements Engineering (IEEE 29148:2018)

Structured requirements elicitation, analysis, specification, and validation following the ISO/IEC/IEEE 29148:2018 standard. This skill takes a **defined problem** and produces formal, testable requirements with full traceability from stakeholder needs through to verification methods.

**This skill does not define the problem.** It assumes the problem is already understood — who has it, what the gap is, and what the solution space looks like. If the problem isn't clear, run `/problem-definition` first. This skill is the bridge between "we understand the problem" and "we have a specification to build against."

## When to Use

- A defined problem exists (from `/problem-definition` or a user-provided problem statement)
- Stakeholder needs must be elicited, documented, and translated into system-level specifications
- Requirements need to be validated against IEEE 29148 quality characteristics
- Traceability from needs to verification is required

## Do NOT Auto-Invoke

This skill produces formal specifications and should not run without explicit request. Invoke with: `/requirements-engineering [problem-statement]`.

## Prerequisites

This skill works best when given a problem definition. It can proceed without one, but the output quality depends on input quality:

| Input provided | What this skill does |
|---------------|---------------------|
| Structured handoff (`.problem-definition/handoff.yaml`) | Imports problem owners, gap analysis, solution space, and frame mechanically. No semantic interpretation needed. Highest quality. |
| Full `/problem-definition` markdown output | Uses problem statement, stakeholders, gap analysis, and solution space via semantic reading. High quality. |
| User-provided problem statement | Validates the statement before proceeding. Ask clarifying questions if the problem is vague. |
| Nothing — just a feature name | Runs a lightweight problem discovery (ask user 3-5 questions) before proceeding. Lower quality — recommend `/problem-definition` for complex problems. |

## Standard Reference

**Source**: ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*
**Scope**: This skill implements Clauses 6.2 (Stakeholder Needs and Requirements Definition) and 6.3 (System Requirements Definition). Clause 6.1 (Business or Mission Analysis) is handled by `/problem-definition`.
**Status**: Current international standard (replaces IEEE 830-1998)

## How This Skill Works

IEEE 29148 defines **what** to produce. This skill also encodes **how to think** — the practitioner judgment that the standard assumes a human already has. Every step includes reasoning guidance, decision rules, and explicit backtracking triggers.

The process is **iterative, not linear**. Later steps routinely reveal problems in earlier steps. When that happens, go back. Backtracking triggers in each section tell you when.

---

## Input Detection

Before beginning the requirements process, detect the input quality tier. This determines how stakeholders, problem context, and constraints are imported.

### Tier 1: Structured Handoff (Highest Fidelity)

Check for `.problem-definition/handoff.yaml`. If found:

1. Validate: `python3 -m scripts.schemas.problem_definition .problem-definition/`
2. If valid: import fields mechanically using the mapping below
3. If invalid or validation fails: fall back to Tier 2

**Structured import mapping**:

| handoff.yaml field | RE step | Mapping |
|---|---|---|
| `problem_owners[]` | Step 1.1: Stakeholder identification | Each `who` becomes a stakeholder row. `priority: primary` → Must priority. `priority: secondary` → Should. `priority: affected` → Could. `experience` seeds the needs summary for Step 1.2. |
| `problem_definition.problem_statement` | Step 1.2: Elicitation scoping | Used as the anchor for "what does [stakeholder] need from this system?" |
| `problem_definition.gap_analysis[]` | Step 1.2: Grounding | Each dimension seeds a specific elicitation question. The `gap` field identifies what must change. |
| `solution_space.classes_excluded[]` | Step 2.1: Feasibility constraints | Excluded solution classes become system requirement constraints — requirements must not prescribe excluded approaches. |
| `solution_space.trade_offs[]` | Step 2.1: Non-functional requirement seeding | Each trade-off suggests a performance, usability, or reliability requirement that needs explicit thresholds. |
| `problem_framing.selected_frame` | Step 1.3: Conflict resolution scope | The frame's `includes`/`excludes` define the boundary for in-scope vs. out-of-scope needs. |
| `problem_classification.type` | Process guidance | If `wicked`: warn that requirements will be provisional and expect iteration. If `mess`: resist decomposition into independent sub-requirements. |
| `quality_gate.all_passed` | Confidence level | If `false`: flag that problem definition needs rework before high-quality requirements engineering. Proceed at lower confidence. |
| `problem_situation.concerns[]` | Step 1.2: Elicitation seeds | Each concern becomes an interview question seed: "How does [concern] affect [stakeholder]?" |

### Tier 2: Markdown Problem Definition

Check for `.problem-definition/problem-definition.md`. If found:

1. Read and semantically parse the six sections
2. Extract problem owners, problem statement, gap analysis, solution space, and frame through reading comprehension
3. Proceed with the existing behavior described throughout this skill

### Tier 3: User-Provided Input

Use `$ARGUMENTS` directly. Current behavior unchanged — validate the statement, ask clarifying questions if vague, or run lightweight discovery (3-5 questions) for bare feature names.

---

## Process 1: Stakeholder Needs and Requirements Definition

**Standard reference**: IEEE 29148:2018, Clause 6.2
**Purpose**: Elicit stakeholder needs and translate them into formal stakeholder requirements.

### Step 1.1: Import or Identify Stakeholders

**If structured handoff is available** (Tier 1): Import `problem_owners` array directly. Map each entry:

- `who` → Stakeholder name/role
- `experience` → Needs summary seed (used in Step 1.2)
- `cost` → Constraints context
- `priority: primary` → Must priority, map to relevant IEEE 29148 category (typically End users or Acquirers)
- `priority: secondary` → Should priority
- `priority: affected` → Could priority

Also import `problem_framing.selected_frame.description` as the scoping context for the requirements process.

**If markdown or no input** (Tier 2/3): If a `/problem-definition` markdown output is available, import the problem owners as the initial stakeholder list. Otherwise, identify them now.

**Stakeholder categories** (IEEE 29148:2018):

| Category | How to identify in an agent context | Include if... |
|----------|-------------------------------------|---------------|
| End users | Who runs this code? Who sees its output? | Always include |
| End user organizations | What team/company do users belong to? | Include if organizational constraints exist |
| Acquirers / customers | Who decides to adopt this? (May be same as users) | Include if different from end users |
| Operators | Who deploys, configures, monitors? | Include if the system runs as a service |
| Supporters / maintainers | Who fixes bugs? Who reviews PRs? | Always include for open-source or team projects |
| Developers / producers | Who builds this? (Often: you, the agent, plus the user) | Always include |
| Regulatory bodies | Are there compliance requirements? | Include only if applicable |

**Identification methods**:

1. **Import from `/problem-definition`**: Use the problem owners table directly. Map "problem owner" roles to IEEE 29148 stakeholder categories.
2. **Ask the user**: "Besides yourself, who else uses/maintains/depends on this?"
3. **Read artifacts**: git log (contributors), CODEOWNERS (maintainers), README (audience), deployment config (operators).

**Depth rule**: For small projects (single developer, personal use), 2-3 stakeholders is sufficient. For shared/production systems, aim for 4-6. More than 8 means you're splitting too finely — consolidate stakeholders who share the same needs.

**Output**:

```markdown
## Stakeholder Analysis

| Stakeholder | Role | Needs (summary) | Constraints | Priority |
|-------------|------|------------------|-------------|----------|
| [Specific name/group] | [Role from table above] | [1-2 sentence summary] | [What they won't accept] | Must / Should / Could |
```

### Step 1.2: Elicit Stakeholder Needs

This is the hardest step. IEEE 29148 assumes interviews and workshops. An agent must substitute different methods.

**Elicitation methods** (use in combination, not isolation):

| Method | When to use | How |
|--------|------------|-----|
| **Direct questioning** | Always — start here | Ask the user structured questions: "What does [stakeholder] need from this system?" "What would make [stakeholder] reject this solution?" |
| **Artifact analysis** | When the user can't fully speak for a stakeholder | Read code, tests, docs, issues, and error logs. Existing tests encode implicit requirements. Error handling reveals assumed failure modes. |
| **Constraint inference** | Always — supplements other methods | Examine the codebase for technical constraints that impose needs: if the system uses SQLite, "must work without a database server" is an implicit need. |
| **Negative elicitation** (Robertson & Robertson) | When needs feel too vague | Ask "What should this system NOT do?" and "What would make this solution worse than the current state?" Boundaries clarify needs. |
| **Scenario walking** | For complex workflows | "Walk me through what happens when [stakeholder] does [task]. Where does it break? Where is it slow? Where is it confusing?" |
| **Goal decomposition** (Van Lamsweerde, KAOS) | When needs are too high-level | Break a high-level goal into sub-goals using AND/OR decomposition. "To achieve [goal], the system must [sub-goal-1] AND [sub-goal-2]." Stop when sub-goals are concrete enough to be verifiable. |

**Judgment rules for elicitation depth**:

- **Stop eliciting** when new questions produce information already captured in existing needs
- **Go deeper** when a need contains ambiguous terms ("fast," "easy," "reliable"), unmeasurable qualities, or implicit assumptions
- **Escalate to the user** when you can't determine a need from available artifacts — don't guess
- **Challenge stated needs**: "You said you need X. What happens if you don't get X?" If the answer is "nothing important," it's a want, not a need. Still record it, but at lower priority.

**Output**:

```markdown
### Stakeholder Needs

#### [Stakeholder Name]
1. **Need:** [Natural language description — concrete, not abstract]
   **Context:** [When/where this need arises — specific scenario, not generic]
   **Priority:** [Must / Should / Could / Won't]
   **Source:** [How this need was identified: user interview, code analysis, doc review, inference]
   **Confidence:** [High: stated by user. Medium: inferred from artifacts. Low: assumed — needs validation]
```

**Backtracking trigger**: If a stakeholder has zero needs, either the stakeholder isn't relevant (remove from Step 1.1) or elicitation was too shallow (try a different method). If a need can't be stated concretely, the problem definition may be too vague — recommend `/problem-definition`.

### Step 1.3: Resolve Conflicts Between Stakeholder Needs

**Do this before writing requirements.** Conflicting needs are the norm, not the exception.

**Conflict detection**: Compare needs across different stakeholders. Common patterns:

| Conflict type | Example | Resolution approach |
|--------------|---------|-------------------|
| **Direct contradiction** | User wants simplicity; maintainer wants configurability | Present both to the user with trade-offs. One must yield. |
| **Resource competition** | Feature A and Feature B both needed, but only time/budget for one | Prioritize by stakeholder priority and business impact. Defer the lower-priority need. |
| **Constraint violation** | A need requires technology excluded by a constraint | Reframe the need to work within constraints, or escalate the constraint for re-evaluation. |
| **Scope disagreement** | One stakeholder wants broad scope; another wants narrow | Align with the problem statement. Needs outside the stated gap are out of scope. |

**Resolution process**:

1. List all conflicts found
2. For each conflict, state which needs are in tension and why
3. Propose a resolution with rationale
4. **Present conflicts to the user for decision** — do not silently resolve conflicts
5. Document the resolution decision

**Output**:

```markdown
### Conflict Resolution

| Conflict | Needs in tension | Resolution | Decided by |
|----------|-----------------|------------|------------|
| [Description] | Need X vs. Need Y | [Which need takes priority, and why] | [User / Agent inference / Default to higher-priority stakeholder] |
```

**Backtracking trigger**: If a conflict can't be resolved without changing the problem statement, recommend re-running `/problem-definition` to reframe.

### Step 1.4: Write Stakeholder Requirements

Transform needs into formal stakeholder requirements. Each requirement MUST satisfy all IEEE 29148 quality characteristics:

| Characteristic | Definition | Test |
|----------------|-----------|------|
| **Necessary** | Required to satisfy a genuine need; not gold-plating | Can you trace it to a stakeholder need? |
| **Implementation-free** | States what is needed, not how to build it | Does it prescribe a specific technology or design? If yes, rewrite. |
| **Unambiguous** | One and only one interpretation | Could two competent people read this differently? If yes, rewrite. |
| **Consistent** | Does not conflict with other requirements | Does it contradict any other requirement? Check against conflict resolution from Step 1.3. |
| **Complete** | Sufficient to define the need without additional information | Are there undefined terms, TBDs, or implicit assumptions? |
| **Singular** | States one requirement, not a compound statement | Does it contain "and" or "or" joining separate requirements? If yes, split. |
| **Feasible** | Achievable within known constraints | Can this be built with available resources, time, and technology? |
| **Traceable** | Links back to a stakeholder need and forward to verification | Is the source need identified? Is a test method identifiable? |
| **Verifiable** | Can be confirmed through inspection, analysis, demonstration, or test | Can you write a pass/fail test for this? If not, rewrite. |

**Writing rules** (per IEEE 29148):

- One requirement per statement — no "and" or "or" joining separate capabilities
- Active voice: "The system shall [verb]..." not passive constructions
- No ambiguous terms without measurable definitions ("fast" must become "< 2 seconds")
- Declarative, not procedural: state what, not how
- Each requirement gets a unique identifier for traceability

**Self-check after writing each requirement**: Run through the characteristics table above. If any check fails, rewrite before moving on. Do not accumulate bad requirements and try to fix them later.

**Output**:

```markdown
### Stakeholder Requirements

| ID | Requirement | Source Need | Priority | Rationale |
|----|------------|-------------|----------|-----------|
| STK-001 | [Active voice, singular, verifiable statement] | [Need ID] | Must/Should/Could/Won't | [Why this requirement exists] |
```

**Backtracking trigger**: If a requirement can't be made verifiable, the underlying need from Step 1.2 is too vague — return and re-elicit. If a requirement can't be made implementation-free, the problem was framed as a solution — recommend `/problem-definition` Step 3 (reframing).

---

## Process 2: System Requirements Definition

**Standard reference**: IEEE 29148:2018, Clause 6.3
**Purpose**: Transform stakeholder requirements into a technical specification that defines what the system must do.

### Step 2.1: Derive System Requirements

For each stakeholder requirement, derive one or more system requirements. Every system requirement must trace to at least one stakeholder requirement. Orphans (no trace) should be deleted or their source found.

**Derivation guidance**:

- A single stakeholder requirement often produces multiple system requirements (functional + non-functional)
- If a stakeholder requirement produces zero system requirements, either it's not a system-level concern (drop it) or it needs deeper analysis
- System requirements MAY prescribe technology when feasibility depends on a specific approach — but document why

**Choosing verification methods**:

| If the requirement is about... | Default method | Rationale |
|-------------------------------|----------------|-----------|
| Observable behavior (user-facing features) | **Demonstration** | Show it works under realistic conditions |
| Measurable performance (speed, throughput, capacity) | **Test** with defined thresholds | Requires quantitative pass/fail criteria |
| Structural properties (modularity, code organization) | **Inspection** | Verified by examining the artifact, not running it |
| Emergent properties (scalability, fault tolerance) | **Analysis** or **Test** under load | May require modeling or stress testing |
| Security properties (access control, data protection) | **Test** + **Inspection** | Both behavioral tests and code/config review |
| Compliance (standards adherence, format conformance) | **Inspection** + **Analysis** | Check against specification documents |

**Output**:

```markdown
## System Requirements

### Functional Requirements

| ID | Requirement | Traces To | Verification Method | Priority |
|----|------------|-----------|-------------------|----------|
| SYS-F-001 | [The system shall...] | STK-001 | [Method with rationale] | Must/Should/Could |

### Non-Functional Requirements

#### Performance
| ID | Requirement | Traces To | Verification Method |
|----|------------|-----------|-------------------|
| SYS-P-001 | [Measurable performance requirement with threshold] | STK-xxx | [Method] |

#### Security
| ID | Requirement | Traces To | Verification Method |
|----|------------|-----------|-------------------|
| SYS-S-001 | [Security requirement] | STK-xxx | [Method] |

#### Usability
| ID | Requirement | Traces To | Verification Method |
|----|------------|-----------|-------------------|
| SYS-U-001 | [Usability requirement] | STK-xxx | [Method] |

#### Reliability
| ID | Requirement | Traces To | Verification Method |
|----|------------|-----------|-------------------|
| SYS-R-001 | [Reliability requirement] | STK-xxx | [Method] |
```

**Backtracking trigger**: If a system requirement can't be derived, return to Step 1.2 and re-elicit the underlying need. If derivation reveals that a stakeholder requirement was ambiguous, return to Step 1.4 and rewrite it.

### Step 2.2: Validate the Requirements Set

Check the requirements set **as a whole**, not just individual requirements. A set of individually correct requirements can still be collectively broken.

| Set Characteristic | Check | How to check | Pass/Fail |
|-------------------|-------|-------------|-----------|
| **Complete** | Does the set cover all stakeholder needs? | Walk the traceability: every need from Step 1.2 should trace through to at least one system requirement. Gaps = missing requirements. | |
| **Consistent** | Do any requirements contradict each other? | Look for pairs where satisfying one makes it impossible to satisfy another. Common: performance vs. security, simplicity vs. completeness. | |
| **Affordable** | Can the full set be implemented within constraints? | Sum estimated effort. If total exceeds constraints, requirements must be cut — start with "Could" priority. | |
| **Bounded** | Is the scope clearly delineated? | Check for open-ended requirements ("support all formats," "handle any input"). These need explicit boundaries. | |

**If validation fails**:

- **Incomplete**: Return to Step 1.2 to elicit missing needs, then derive in Step 2.1
- **Inconsistent**: Return to Step 1.3 to resolve the conflict
- **Unaffordable**: Present the priority list to the user. Cut "Could" first, then "Should." Never silently cut "Must."
- **Unbounded**: Rewrite the open-ended requirements with explicit scope limits

### Step 2.3: Build Traceability Matrix

Build a full traceability matrix only if the requirements set has more than ~10 system requirements. For smaller sets, the "Traces To" column in the requirements tables provides sufficient traceability.

```markdown
## Requirements Traceability Matrix

| Stakeholder Need | Stakeholder Req | System Req | Verification |
|-----------------|-----------------|------------|-------------|
| [Need description] | STK-001 | SYS-F-001, SYS-P-001 | [Method]: [specific test/check] |
```

**Completeness checks**:

- **Every need** must have at least one stakeholder requirement
- **Every stakeholder requirement** must have at least one system requirement
- **Every system requirement** must have a verification method
- **Orphan system requirements** (no trace to a stakeholder requirement) should be deleted or justified
- **Gaps** (a need with no system requirement) must be filled or explicitly descoped with rationale

---

## Iteration Protocol

| Trigger | What happened | Go back to |
|---------|--------------|------------|
| Stakeholder has zero needs in Step 1.2 | Not relevant or elicitation too shallow | Step 1.1 (remove) or try different elicitation method |
| Need is too vague to formalize in Step 1.4 | Elicitation was incomplete | Step 1.2, using a different method |
| Requirement is a solution statement in Step 1.4 | Problem was framed as a solution | Recommend `/problem-definition` |
| Stakeholder needs conflict in Step 1.3 | Incompatible needs | Present to user for decision; document resolution |
| Can't derive system requirement in Step 2.1 | Stakeholder requirement is ambiguous | Step 1.4 to rewrite, or Step 1.2 to re-elicit |
| Validation fails in Step 2.2 | Set-level problem | Depends on failure type (see Step 2.2) |
| Traceability has gaps in Step 2.3 | Missing or unnecessary requirements | Step 1.2 for gaps; delete orphans |

**Iteration limit**: If you've looped through the same step three times without progress, stop and escalate to the user. State what's blocking and what information is needed.

---

## Output Format

```markdown
# Requirements Specification: [Topic]

**Date:** [timestamp]
**Standard:** ISO/IEC/IEEE 29148:2018
**Status:** Draft / Under Review / Approved
**Problem definition source:** [/problem-definition output, user-provided, or lightweight discovery]

## 1. Stakeholder Requirements
### 1.1 Stakeholder Analysis
[Step 1.1 output — stakeholder table]

### 1.2 Stakeholder Needs
[Step 1.2 output — needs with confidence levels]

### 1.3 Conflict Resolution
[Step 1.3 output — conflicts, resolutions, decisions]

### 1.4 Stakeholder Requirements Specification
[Step 1.4 output — formal requirements, all quality characteristics met]

## 2. System Requirements
### 2.1 Functional Requirements
[Step 2.1 functional output]

### 2.2 Non-Functional Requirements
[Step 2.1 non-functional output]

### 2.3 Requirements Validation
[Step 2.2 output — set-level checks]

### 2.4 Traceability Matrix
[Step 2.3 output — only if >10 system requirements]

## Iterations
[Document any backtracking that occurred: what triggered it, what changed]

## Provenance
- **Standard:** ISO/IEC/IEEE 29148:2018
- **Problem definition:** [Link to /problem-definition output, or inline problem statement]
- **Applied by:** [agent/user]
- **Status:** Living document — requirements evolve with understanding
```

## Quality Gate

Before marking requirements as complete, every requirement MUST pass this checklist (derived from IEEE 29148 Section 5.2.8). Apply this at Step 1.4 per-requirement, not as a batch check at the end:

- [ ] **Necessary**: Traces to a real stakeholder need
- [ ] **Implementation-free**: Does not prescribe design
- [ ] **Unambiguous**: Single interpretation only
- [ ] **Consistent**: No contradictions with other requirements (checked in Step 1.3)
- [ ] **Complete**: No TBDs, no undefined terms
- [ ] **Singular**: One requirement per statement
- [ ] **Feasible**: Achievable within constraints
- [ ] **Traceable**: Forward and backward links exist
- [ ] **Verifiable**: Pass/fail test can be written

Any requirement that fails a checkbox needs rework at the relevant step, not a waiver.

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `problem-definition` | Primary upstream input. `/problem-definition` produces the problem statement, stakeholders, gap analysis, and solution space that this skill consumes. Recommended for complex or unclear problems. |
| `gate-decision` | Requirements quality can serve as a gate signal. Incomplete traceability = REVISE. |
| `testing-strategy` | Verification methods from Step 2.1 feed directly into test strategy selection. |
| `process-map` | Process maps provide context for understanding stakeholder workflows during elicitation (Step 1.2, scenario walking method). |

## References

- ISO/IEC/IEEE 29148:2018. *Systems and software engineering — Life cycle processes — Requirements engineering*. ISO/IEC/IEEE. — Primary standard. Clauses 6.2 and 6.3 are the basis for this skill's two processes.
- ISO/IEC/IEEE 15288:2023. *Systems and software engineering — System life cycle processes*. Clause 6.4.2 (Stakeholder Needs and Requirements Definition), Clause 6.4.3 (System Requirements Definition). — Complementary life cycle standard.
- Van Lamsweerde, A. (2009). *Requirements Engineering: From System Goals to UML Models to Software Specifications*. Wiley. — KAOS goal-oriented requirements engineering. Source for goal decomposition technique in Step 1.2. Obstacle analysis informs conflict detection in Step 1.3.
- Wiegers, K. & Beatty, J. (2013). *Software Requirements* (3rd ed.). Microsoft Press. — Elicitation techniques (Chapter 7) and conflict resolution heuristics (Chapter 16) adapted in Steps 1.2 and 1.3.
- Robertson, S. & Robertson, J. (2012). *Mastering the Requirements Process* (3rd ed.). Addison-Wesley. — Negative elicitation technique adapted in Step 1.2.
- Zave, P. & Jackson, M. (1997). "Four Dark Corners of Requirements Engineering." *ACM TOSEM*, 6(1), 1-30. — The distinction between requirements (environment constraints) and specifications (machine behavior). Source for the principle that requirements describe the problem domain, not the solution.
