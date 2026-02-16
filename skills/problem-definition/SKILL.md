---
name: problem-definition
description: Structured problem definition before requirements engineering. Identifies the real problem, who has it, and what the gap is. Use ONLY when explicitly invoked.
argument-hint: [problem-statement or situation-description]
disable-model-invocation: true
---

# Problem Definition

Structured exploration, framing, and articulation of a problem before any requirements or solution work begins. This skill answers the question every engineering effort must start with: **"What is the actual problem?"**

This is distinct from requirements engineering. Requirements engineering assumes an understood problem and formalizes it into specifications. This skill produces the understood problem. As Jackson (2001) argues: you must analyze the problem world before you can specify what any machine should do within it. As Gause & Weinberg (1990) observe: "The fledgling problem solver invariably rushes in with solutions before taking time to define the problem being solved."

**This is a problem-definition pathway.** A downstream consumer is `/requirements-engineering`, which takes a defined problem and produces formal specifications.

## When to Use

- Before `/requirements-engineering` when the problem isn't yet clear
- When a user says "I want to build X" but hasn't articulated why or for whom
- When multiple stakeholders disagree on what the problem is
- When a proposed solution exists but the underlying problem hasn't been stated
- When prior attempts to solve a problem have failed and the framing needs examination

## Do NOT Auto-Invoke

This skill should not run without explicit request. Invoke with: `/problem-definition [situation-description]`.

## Theoretical Foundations

This skill synthesizes nine established frameworks for problem definition, each contributing a specific capability:

| Source | Key contribution | Used in |
|--------|-----------------|---------|
| **Jackson, Problem Frames (2001)** | Problem analysis is distinct from requirements specification. Understand the problem domain before specifying machine behavior. | Overall structure; problem-domain focus |
| **Gause & Weinberg, Are Your Lights On? (1990)** | Four heuristics: identify the problem, determine the owner, find where it came from, decide whether to solve it. | Steps 1-4 |
| **Checkland, Soft Systems Methodology (1981)** | Distinguish the "problem situation" (rich, messy, multi-perspective) from the "problem statement" (crystallized, actionable). Explore the situation before stating the problem. | Step 1 (Situation Exploration) |
| **Ackoff, The Art of Problem Solving (1978)** | Problems are interconnected systems ("messes"). Formulate the mess before extracting individual problems. A problem extracted from its mess loses its essential properties. | Step 1 (recognizing interconnection) |
| **Rittel & Webber, Dilemmas in a General Theory of Planning (1973)** | Some problems are "wicked" — they have no definitive formulation, the definition depends on the solution, and they are essentially unique. Recognize wickedness early. | Step 2 (Problem Classification) |
| **Dorst, Frame Innovation (2015)** | Problem framing is a creative act distinct from problem solving. Different frames make different solutions visible. Reframing can dissolve problems that seem intractable. | Step 3 (Problem Framing) |
| **Kepner-Tregoe, The New Rational Manager (1981)** | Situation Appraisal (list, clarify, prioritize concerns) must precede Problem Analysis (IS/IS-NOT deviation analysis). | Step 1 (listing concerns); Step 5 (IS/IS-NOT gap) |
| **IEEE 15288:2023, Clause 6.4.1** | Business or Mission Analysis: establish the problem/opportunity and identify potential solution classes before stakeholder needs definition. | Step 5 (Gap Analysis); Step 6 (Solution Space) |
| **IEEE 29148:2018, Clause 6.1** | Business or Mission Analysis as the first requirements engineering process — understanding the problem context before eliciting needs. | Step 5 (Gap Analysis); integration with `/requirements-engineering` |

## Process

Six steps. The process is iterative — later steps may reveal that earlier steps were incomplete. Backtracking triggers are noted in each step.

---

### Step 1: Explore the Problem Situation

**Source**: Checkland (SSM), Ackoff (mess formulation), Kepner-Tregoe (situation appraisal)

**Purpose**: Understand the messy reality before trying to name a clean problem. Checkland's key insight: "Problems do not exist independent of human beings. Look not at the problem but at the situation."

**Do not start with a problem statement.** Start with a situation. The problem statement is an output of this skill, not an input.

**Exploration methods** (for an agent context):

| Method | When to use | How |
|--------|------------|-----|
| **Ask the user to describe the situation** | Always — start here | "Describe what's happening. Don't tell me the problem yet — tell me the situation." Follow up: "What else is going on around this?" |
| **List all concerns** (Kepner-Tregoe) | When the situation feels tangled | "What are all the things that bother you about this? List them without prioritizing." This separates the mess into visible threads. |
| **Read existing artifacts** | When the user can't fully articulate the situation | README, issue trackers, PR descriptions, commit messages, error logs, user complaints, support tickets. These contain fragments of the problem situation. |
| **Examine the codebase** | For technical problems | Architecture, test failures, TODOs, workarounds, dead code, performance profiles. These reveal pain points the user may not have named. |
| **Map the interconnections** (Ackoff) | When concerns seem related | "Does concern A affect concern B? Would solving A change the nature of B?" Problems that are part of a mess can't be solved independently. |

**Judgment rules**:

- **Go wide before going deep.** List all concerns before investigating any one concern in detail.
- **Resist naming the problem early.** If the user offers a problem statement in the first sentence, acknowledge it but keep exploring. The stated problem is often a symptom or a premature solution.
- **Stop exploring** when new questions produce information that fits into already-identified concerns without revealing new ones.

**Output**:

```markdown
## Problem Situation

### Context
[What is happening. The environment, the people, the systems, the workflows involved.]

### Concerns
1. [Concern] — [Who raised it or where it was observed]
2. [Concern] — [Source]
...

### Interconnections
[Which concerns are related. Which might be symptoms of deeper issues. Which are independent.]

### Prior Attempts
[What has been tried before. What happened. Why it didn't fully work.]
```

**Backtracking trigger**: None — this is the starting point.

---

### Step 2: Classify the Problem

**Source**: Rittel & Webber (wicked problems), Jackson (problem frames)

**Purpose**: Determine what kind of problem this is, because different kinds of problems require different approaches. Not all problems can be "solved" — some can only be managed.

**Classification**:

| Type | Characteristics | Implications |
|------|----------------|-------------|
| **Tame** | Clear definition, known solution approaches, definitive test of success | Proceed directly to gap analysis (Step 5). Standard engineering applies. |
| **Complicated** | Clear definition, but multiple interacting parts. Expertise needed, but solvable. | May need decomposition before gap analysis. Watch for emergent interactions. |
| **Wicked** (Rittel & Webber) | No definitive formulation. The definition depends on the solution. Stakeholders disagree on the problem itself. Every attempt to solve it changes the problem. | Do NOT proceed to formal requirements. Use Step 3 (Problem Framing) to surface framing assumptions. Accept that the problem definition will evolve. |
| **Mess** (Ackoff) | A system of interconnected problems. No single problem can be extracted and solved independently. | Identify the most leveraged intervention point. Resist decomposing into independent sub-problems. |

**How to classify** (apply these tests):

1. **Can two competent people agree on what the problem is?** If no → likely wicked.
2. **Does the problem change when you try to solve it?** If yes → wicked.
3. **Can the problem be stated without implying a solution?** If no → the "problem" may actually be a solution in disguise.
4. **Is this one problem or several tangled together?** If tangled → mess.
5. **Has this exact problem been solved before in a similar context?** If yes → tame.

**Output**:

```markdown
### Problem Classification
- **Type:** [Tame / Complicated / Wicked / Mess]
- **Evidence:** [Which tests led to this classification]
- **Implication:** [What this means for the approach]
```

**Backtracking trigger**: If classification reveals the problem is wicked, spend extra time on Step 3 (Problem Framing) to surface hidden assumptions. This skill can still produce useful output for wicked problems, but the user should know the definition will be provisional.

---

### Step 3: Frame the Problem

**Source**: Dorst (Frame Innovation), Checkland (SSM worldviews), Gause & Weinberg (whose problem is it?)

**Purpose**: Choose the lens through which to view the problem situation. Different frames make different problems visible and different solutions possible.

**Why framing matters**: Dorst's key insight: a problem that appears intractable within one frame may dissolve when reframed. The frame is not the problem — it's the perspective that makes the problem visible.

**Framing method**:

1. **Identify the current frame**: How is the problem currently being talked about? What metaphor or mental model is in use? ("This is a performance problem" vs. "This is a workflow problem" vs. "This is a communication problem" — these are different frames of potentially the same situation.)

2. **Name the stakeholder behind the frame** (Gause & Weinberg): Every problem definition serves someone's perspective. Ask: "Whose problem is this? Who decided it was a problem? Who benefits from it being framed this way?"

3. **Generate alternative frames**: Deliberately re-describe the situation from at least two other perspectives. Use these prompts:
   - "If [different stakeholder] described this situation, what would they say the problem is?"
   - "If this isn't a [current frame] problem, what kind of problem could it be?"
   - "What if the 'problem' is actually a symptom? What would the underlying problem be?"

4. **Select the working frame**: Choose the frame that best explains the concerns from Step 1 and that opens the most productive solution space. Document why.

**Output**:

```markdown
### Problem Framing

#### Current Frame
[How the problem is currently being described. Who holds this frame.]

#### Alternative Frames
1. [Alternative frame] — [What it reveals that the current frame doesn't]
2. [Alternative frame] — [What it reveals]

#### Selected Frame
[Which frame will be used going forward, and why.]
[What this frame includes and what it excludes.]
```

**Backtracking trigger**: If no frame adequately explains the concerns from Step 1, return to Step 1 — the situation exploration was too shallow. If the user disagrees with the selected frame, explore their reasoning — they may have situational knowledge that makes a different frame more appropriate.

---

### Step 4: Identify Who Has the Problem

**Source**: Gause & Weinberg (problem ownership), IEEE 15288 (stakeholder identification), IEEE 29148 (stakeholder categories)

**Purpose**: A problem without an owner is an abstraction. Identifying who specifically experiences the problem makes it concrete and testable.

**Gause & Weinberg's heuristic**: "Who has a problem?" followed by "What is their problem?" — not the reverse. Start with people, not with problem statements.

**Identification methods** (for an agent context):

1. **Ask the user**: "Besides yourself, who else is affected by this situation?"
2. **Derive from the frame**: The frame selected in Step 3 implies affected parties. A "performance problem" affects end users. A "maintainability problem" affects developers. A "cost problem" affects budget holders.
3. **Read artifacts**: git log (contributors), CODEOWNERS (maintainers), README (audience), deployment config (operators), issue tracker (reporters).
4. **Check IEEE 29148 categories**: End users, acquirers, operators, maintainers, developers, regulators. For each, ask: "Does this situation affect them? How?"

**Depth rule**: For small projects (1 developer, personal use), 2-3 problem owners is sufficient. For shared systems, 3-5. If you identify more than 6, consolidate those who experience the same problem in the same way.

**For each problem owner, capture**:

```markdown
### Problem Owners

| Who | How they experience the problem | What they lose (cost of the problem) | Priority |
|-----|-------------------------------|--------------------------------------|----------|
| [Specific person/role/group] | [Their concrete experience of the situation] | [Time, money, quality, safety, satisfaction] | Primary / Secondary / Affected |
```

**The "cost of the problem" column is critical.** If no one can articulate what they lose, the problem may be hypothetical. This is Gause & Weinberg's test: "What happens if this problem isn't solved?" If the answer is "nothing much," it's not a problem — it's a preference.

**Backtracking trigger**: If no one can be identified as experiencing the problem, return to Step 1 — either the situation wasn't explored enough, or the problem is hypothetical. If the problem owners disagree on what the problem is, return to Step 3 — the frame may be too narrow or the wrong frame was selected.

---

### Step 5: Define the Gap

**Source**: IEEE 29148 Clause 6.1 (Business/Mission Analysis), Kepner-Tregoe (IS/IS-NOT), IEEE 15288 Clause 6.4.1

**Purpose**: Crystallize the problem into its most concrete, testable form: the specific gap between the current state and the desired state.

**This is where the problem statement is produced.** Everything before this step was preparation. A problem statement written without Steps 1-4 is a guess.

**Gap analysis method** (adapted from Kepner-Tregoe IS/IS-NOT):

| Dimension | IS (current state) | IS NOT (desired state) | Gap |
|-----------|-------------------|----------------------|-----|
| **What** is happening | [Observable behaviors, outputs, failures] | [What should be happening instead] | [Specific difference] |
| **Where** it happens | [Systems, components, contexts affected] | [Where it doesn't happen, or shouldn't happen] | [Scope boundary] |
| **When** it happens | [Conditions, triggers, frequency] | [When it doesn't happen] | [Pattern] |
| **Who** is affected | [From Step 4] | [Who is not affected, and why] | [Distinguishing factor] |
| **How much** | [Severity, frequency, cost] | [Acceptable threshold] | [Measurable delta] |

**Writing the problem statement**:

Combine the gap analysis into a single statement that is:
- **Specific**: Names who, what, where, when
- **Measurable**: Includes the "how much" gap
- **Factual**: Describes observable state, not opinions
- **Solution-free**: Does not imply a particular fix

**Test the statement** (Gause & Weinberg's final heuristic): "Do we really want to solve this?" Some problems, once clearly defined, turn out not to be worth solving. The cost of the problem is less than the cost of any solution. This is a legitimate and valuable conclusion.

**Output**:

```markdown
## Problem Definition

### Gap Analysis
[IS/IS-NOT table from above]

### Problem Statement
[One to three sentences. Specific, measurable, factual, solution-free.]

### Cost of the Problem
[What is lost by not solving this. Time, money, quality, user experience, risk.]

### Worth Solving?
[Yes/No. If no, explain why and stop here. A well-defined problem that isn't worth solving is a successful outcome of this skill.]
```

**Backtracking trigger**: If the IS/IS-NOT analysis reveals that the "desired state" is actually a specific solution ("the desired state is that we use Redis"), return to Step 3 — the problem has been framed as a solution. Reframe it in terms of what capability or outcome is needed, not what technology to use. If the gap can't be stated concretely, return to Step 1 — the situation isn't understood well enough.

---

### Step 6: Characterize the Solution Space

**Source**: IEEE 15288 Clause 6.4.1 (Business or Mission Analysis), Jackson (problem frames — bounding the machine context)

**Purpose**: Before handing off to requirements engineering, bound what kinds of solutions are feasible. This prevents requirements work on solutions that can't be built.

**Investigation methods**:

1. **Examine the codebase** for existing partial solutions, related features, or architectural patterns that constrain what's possible
2. **Check for prior art** in the project's history — closed issues, reverted PRs, abandoned branches
3. **Identify architectural constraints** — the existing system's structure limits what solutions are feasible regardless of what's theoretically possible
4. **Assess the problem type** from Step 2 — tame problems have well-known solution classes; wicked problems may not

**Output**:

```markdown
### Solution Space
- **Solution classes considered:** [What types of solutions are possible, given existing architecture and constraints]
- **Solution classes excluded:** [What's out of scope, and why — technical infeasibility, cost, user preference, constraint violation]
- **Key trade-offs:** [What must be balanced — e.g., simplicity vs. flexibility, speed vs. correctness]
- **Existing partial solutions:** [What already exists that addresses part of this problem]
- **Recommended next step:** [/requirements-engineering or "this problem is not worth solving"]
```

**Backtracking trigger**: If no feasible solution class exists, either the constraints from Step 5 are too tight (return and re-examine) or the problem needs reframing (return to Step 3). If the problem was classified as wicked in Step 2, note that the solution space is inherently unstable and will shift as understanding develops.

---

## Iteration Protocol

| Trigger | What happened | Go back to |
|---------|--------------|------------|
| Can't list concerns in Step 1 | Not enough information | Ask user for more context about the situation |
| Problem is wicked in Step 2 | Standard decomposition won't work | Spend extra time on Step 3 (Problem Framing); continue with provisional framing |
| No frame explains the concerns in Step 3 | Situation exploration was too shallow | Step 1 |
| No one experiences the problem in Step 4 | Problem is hypothetical | Step 1, or conclude the problem isn't real |
| Gap can't be stated concretely in Step 5 | Problem isn't understood enough | Step 1 or Step 3 |
| Desired state is a solution in Step 5 | Problem was framed as a solution | Step 3 |
| No feasible solution class in Step 6 | Wrong problem or wrong constraints | Step 3 (reframe) or Step 5 (re-examine constraints) |

**Iteration limit**: If you've looped through the same step three times without progress, stop and escalate to the user. State what's blocking progress and what information you need.

---

## Output Format

```markdown
# Problem Definition: [Topic]

**Date:** [timestamp]
**Status:** Draft / Under Review / Validated

## 1. Problem Situation
[Step 1 output — context, concerns, interconnections, prior attempts]

## 2. Problem Classification
[Step 2 output — type, evidence, implications]

## 3. Problem Framing
[Step 3 output — current frame, alternatives, selected frame with rationale]

## 4. Problem Owners
[Step 4 output — who has the problem, how they experience it, what it costs them]

## 5. Problem Definition
### 5.1 Gap Analysis
[Step 5 IS/IS-NOT table]

### 5.2 Problem Statement
[Specific, measurable, factual, solution-free]

### 5.3 Worth Solving?
[Yes/No with rationale]

## 6. Solution Space
[Step 6 output — feasible classes, exclusions, trade-offs, next step recommendation]

## Iterations
[Document any backtracking that occurred: what triggered it, what changed]

## Provenance
- **Frameworks applied:** [Which of the seven sources were most relevant]
- **Defined by:** [agent/user]
- **Boundary critique reference:** [link if also run, or "not run"]
- **Status:** [Draft — to be consumed by /requirements-engineering or other downstream skill]
```

## Output Directory

All problem-definition outputs are written to `.problem-definition/`:

```text
.problem-definition/
  handoff.yaml              # Structured YAML (machine-consumable contract)
  problem-definition.md     # Human-readable markdown (format above)
```

The markdown is for human consumption. The YAML handoff is the structured contract that enables mechanical consumption by downstream skills (especially `/requirements-engineering`).

## Structured Handoff Output

In addition to the markdown output, write a structured YAML handoff file to `.problem-definition/handoff.yaml`. This enables `/requirements-engineering` to import problem owners, gap analysis, solution space, and framing mechanically rather than through semantic parsing.

**Template**: Use `skills/problem-definition/templates/handoff.yaml` as the reference. All fields from the six process steps map to YAML keys. The handoff envelope mirrors the sprint pattern (`_schema_version`, `phase`, `phase_name`, `skill`, `status`, `timestamp`, `depends_on`, `summary`, `outputs`, `open_issues`, `signals`).

**Key mapping from process steps to YAML**:

| Step | YAML section | Notes |
|------|-------------|-------|
| Step 1: Situation | `problem_situation` | `concerns` is a list of `{concern, source}` objects |
| Step 2: Classification | `problem_classification` | `type` is an enum: tame, complicated, wicked, mess |
| Step 3: Framing | `problem_framing` | Contains `current_frame`, `alternative_frames[]`, `selected_frame` |
| Step 4: Owners | `problem_owners` | List of `{who, experience, cost, priority}` — feeds directly into RE Step 1.1 |
| Step 5: Gap/Statement | `problem_definition` | `gap_analysis[]` has 5 standard dimensions; `problem_statement` is the crystallized statement |
| Step 6: Solution Space | `solution_space` | `classes_excluded[]` feeds into RE Step 2.1 as feasibility constraints |

**Quality gate**: The `quality_gate` section in the handoff mechanizes the 7 checks listed below. Set each field to `true` only if the corresponding check passes. `all_passed` must equal the AND of all individual fields.

**Validation**: After writing the handoff file, validate it:

```bash
python3 -m scripts.schemas.problem_definition .problem-definition/
```

If validation fails, fix the indicated fields before marking the problem definition as complete.

## Quality Gate

Before marking a problem definition as complete, it must pass these checks:

- [ ] **Problem statement is solution-free**: Does not prescribe technology, design, or implementation approach
- [ ] **Problem statement is specific**: Names who is affected, what the gap is, and where/when it manifests
- [ ] **Problem statement is measurable**: Includes quantifiable gap or clear observable behavior
- [ ] **Problem owners are identified**: At least one real person/role experiences this problem with a stated cost
- [ ] **Worth-solving assessment is explicit**: The user has seen the cost of the problem and agreed it warrants engineering effort
- [ ] **Frame is stated**: The perspective used to define the problem is explicit, not hidden
- [ ] **Solution space is bounded**: At least one feasible solution class exists

A problem definition that fails any check needs rework at the relevant step, not a waiver.

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `requirements-engineering` | Primary downstream consumer. This skill produces the problem definition; `/requirements-engineering` formalizes it into specifications. The problem statement, stakeholder list, constraints, and solution space from this skill feed directly into the requirements process. |
| `gate-decision` | Problem definition quality can serve as a gate signal. No clear problem statement = REVISE. |
| `process-map` | Process maps provide context for understanding workflows during situation exploration (Step 1). |

## References

- Ackoff, R. L. (1978). *The Art of Problem Solving*. Wiley. — "Mess formulation": problems are interconnected systems that lose their essential properties when decomposed. Source for interconnection analysis in Step 1.
- Checkland, P. (1981). *Systems Thinking, Systems Practice*. Wiley. — Soft Systems Methodology: explore the "problem situation" before crystallizing a "problem statement." Source for the situation-first approach in Step 1.
- Dorst, K. (2015). *Frame Innovation: Create New Thinking by Design*. MIT Press. — Problem framing as a distinct creative act. Nine-step frame creation process. Source for Step 3.
- Gause, D. C. & Weinberg, G. M. (1990). *Are Your Lights On? How to Figure Out What the Problem Really Is*. Dorset House. — Four problem-definition heuristics: identify it, find the owner, find the source, decide whether to solve it. Source for Steps 4 and 5.
- Jackson, M. (2001). *Problem Frames: Analysing and Structuring Software Development Problems*. Addison-Wesley. — Problem analysis as distinct from requirements specification. The problem domain must be understood before the machine can be specified. Source for the overall separation of this skill from requirements engineering.
- Kepner, C. H. & Tregoe, B. B. (1981). *The New Rational Manager*. Princeton Research Press. — Situation Appraisal and IS/IS-NOT problem analysis. Source for concern listing in Step 1 and gap analysis in Step 5.
- Rittel, H. W. J. & Webber, M. M. (1973). "Dilemmas in a General Theory of Planning." *Policy Sciences*, 4(2), 155-169. — Ten properties of wicked problems. Source for problem classification in Step 2.
- ISO/IEC/IEEE 15288:2023. *Systems and software engineering — System life cycle processes*. Clause 6.4.1 (Business or Mission Analysis). — Problem/opportunity identification and solution space characterization as a process distinct from stakeholder needs definition.
- ISO/IEC/IEEE 29148:2018. *Systems and software engineering — Life cycle processes — Requirements engineering*. Clause 6.1 (Business or Mission Analysis). — Business context and gap analysis as the first process before requirements elicitation.
- Zave, P. & Jackson, M. (1997). "Four Dark Corners of Requirements Engineering." *ACM TOSEM*, 6(1), 1-30. — The environment is "not the most important thing — it is the only thing." Requirements are constraints on the environment, not descriptions of the machine.
