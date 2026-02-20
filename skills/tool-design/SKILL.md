---
name: tool-design
description: Design standards for building skills, commands, and agents. Use when creating or modifying plugin tools — or when planning multi-phase workflows like the sprint lifecycle.
model: opus
---

# Tool Design Guide

**You are designing a component for the plugin system.** Use this reference to determine the correct type, structure, documentation, and composition for any piece of work.

## Component Taxonomy

### Skill — Knowledge & Criteria

A skill is **declarative knowledge** that informs how work should be done. Industry analogy: a **standard operating procedure**, **design specification**, or **policy document** — reference material that a practitioner reads and applies.

| Property | Value |
|----------|-------|
| Purpose | Inform decisions, define criteria, provide patterns |
| Side effects | None — skills guide, they don't execute |
| Invocation | Auto-applied when description matches context, or `/skill-name` |
| Location | `skills/<name>/SKILL.md` |
| Size | 100-200 lines target, 400 max |

**A skill answers:** "What should I check? What criteria apply? What patterns should I follow?"

**Examples:** `gate-decision` (ship/no-ship criteria), `security-review` (vulnerability checklist), `tdd-workflow` (TDD methodology), `composition-patterns` (design patterns catalog)

---

### Command — Workflow & Side Effects

A command is an **imperative workflow** that coordinates actors and produces side effects. Industry analogy: a **CI/CD pipeline stage**, **runbook procedure**, or **automated workflow** — sequenced steps that change system state.

| Property | Value |
|----------|-------|
| Purpose | Execute steps, manage state, produce outputs |
| Side effects | Yes — runs tools, writes files, invokes agents |
| Invocation | User types `/command-name` |
| Location | `commands/<name>.md` |
| Size | 50-80 lines (simple), 80-120 (orchestrator), 150 max |

**A command answers:** "What steps run in what order? What state changes? What happens on failure?"

**Examples:** `ci` (run build/test/lint pipeline), `push` (git push with PR creation), `orchestrate` (sequence agents through phases), `collect-signals` (gather post-merge data)

---

### Agent — Domain Expert

An agent is a **specialist persona** with bounded expertise and a constrained toolset. Industry analogy: a **subject matter expert** or **specialist contractor** — engaged for specific knowledge, given specific tools, expected to produce specific deliverables within a defined scope.

| Property | Value |
|----------|-------|
| Purpose | Apply domain expertise to produce deliverables |
| Side effects | Through tools — agents act within their granted scope |
| Invocation | Called by commands or workflows, not directly by users |
| Location | `agents/<name>.md` |
| Size | 100-150 lines target, 200 max |

**An agent answers:** "Given my expertise and these tools, what does this work need?"

**Examples:** `tdd-guide` (TDD specialist), `code-reviewer` (senior reviewer), `qa-agent` (QA specialist), `architect` (system design), `security-reviewer` (vulnerability assessment)

---

## Decision Framework

```text
Is it knowledge, criteria, or patterns that guide work?
  YES --> Skill

Does it execute a workflow with side effects and state management?
  YES --> Command

Is it a specialist persona with bounded expertise and tools?
  YES --> Agent
```

**Compound test:** If a piece of work both *knows things* AND *does things*, split it:

```text
"Run security analysis" decomposes into:
  security-review/SKILL.md   -- what to check (criteria, checklists)
  security-reviewer agent    -- who checks (persona, expertise, tools)
  code-review command        -- when/how to run (workflow, state, sequencing)
```

**The split test:** If you're writing "and" in the description — "checks security *and* manages the review workflow *and* writes the report file" — that's three components, not one.

---

## Industry-Standard Roles

Each agent or skill maps to a real professional role. Use these scopes to prevent overlap and ensure each component stays in its lane.

| Role | Professional Scope | Delivers | Does NOT Do |
|------|--------------------|----------|-------------|
| **Product Manager** | Translates business needs into requirements. Prioritizes features, defines success metrics, sets scope boundaries. | User stories, acceptance criteria, MoSCoW priority, scope definition | Write code, make architecture decisions |
| **UX Designer** | Defines interaction patterns, user flows, component states, validation rules, accessibility, edge cases. | Flow diagrams, component specs, validation rules | Implement UI, choose frameworks |
| **Systems Architect** | Designs system structure, defines component interfaces, makes technology decisions, assesses cross-cutting concerns. | Architecture decisions, dependency analysis, risk register, ADRs | Write implementation code, manage tasks |
| **Tech Lead** | Plans implementation approach for a feature, breaks work into tasks, orders by dependency, estimates effort. | Task breakdown, execution order, estimates, technical notes | Design system architecture, set product direction |
| **Developer** | Implements tasks using TDD. Writes tests first, then minimal code to pass. Follows established patterns. | Working code, passing tests, execution log | Review own code, make scope decisions |
| **Code Reviewer** | Reviews diffs for quality, security surface, pattern compliance, maintainability. Multiple perspectives intentional. | Review findings with severity, approval/block decision | Fix the code, run the CI pipeline |
| **Security Engineer** | Identifies vulnerabilities (OWASP Top 10), assesses threat surface, rates severity, provides remediation guidance. | Vulnerability findings, severity ratings, remediation steps | Implement fixes, approve for merge |
| **QA Engineer** | Verifies acceptance criteria are met. Runs regression, edge case, and compliance checks. | Test results, coverage report, acceptance criteria status | Write production code, make design decisions |
| **DevOps Engineer** | Runs build/test/lint pipeline. Manages CI/CD execution, reports pass/fail with details. | Build status, lint results, type check results, pipeline report | Fix code issues, make architecture decisions |
| **Release Manager** | Makes go/no-go decision by aggregating signals from review, security, QA, and CI. Manages merge and release. | Gate decision (SHIP/REVISE/BLOCKED), PR, merge status | Write code, run tests, perform reviews |
| **SRE** | Monitors post-deployment health. Collects real signals: build trends, coverage deltas, error rates, dependency health. | Signal report with trends, health assessment, actionable items | Subjective assessments, fix code |
| **Scrum Master** | Facilitates retrospective analysis. Evaluates what worked, what didn't, estimation accuracy, process improvements. | Retrospective analysis, improvement items, next-sprint intake | Make technical decisions, write code |

### Role-to-Phase Mapping

| Phase | Role | Component Type | Implementation |
|-------|------|----------------|----------------|
| 1. Intake | Developer (human) | Skill (sprint) | `skills/sprint/SKILL.md` |
| 2. Refinement | Product Manager | Skill (sprint) | `skills/sprint/SKILL.md` |
| 3. Design | UX Designer | Skill (sprint) | `skills/sprint/SKILL.md` |
| 4. Technical Planning | Systems Architect | Skill (sprint) + Agent | `skills/sprint/SKILL.md`, `agents/architect.md` |
| 5. Backlog | Tech Lead | Skill (sprint) | `skills/sprint/SKILL.md` |
| 6. Implementation | Developer | Agent + Command | `agents/tdd-guide.md`, `commands/tdd.md` |
| 7. Code Review | Code Reviewer | Agent + Command | `agents/code-reviewer.md`, `commands/code-review.md` |
| 8. Security Review | Security Engineer | Agent + Skill | `agents/security-reviewer.md`, `skills/security-review/` |
| 9. QA Validation | QA Engineer | Agent + Command + Skill | `agents/qa-agent.md`, `commands/qa.md`, `skills/verification-loop/` |
| 10. CI/CD | DevOps Engineer | Command | `commands/ci.md`, `commands/verify.md` |
| 11. Merge | Release Manager | Skill + Command | `skills/gate-decision/`, `commands/push.md` |
| 12. Monitoring | SRE | Command | `commands/collect-signals.md` |
| 13. Retrospective | Scrum Master | Skill | `skills/sprint-retrospective/`, `skills/feedback-synthesizer/` |

---

## Design Principles

### 1. Single Responsibility

Each component does exactly one thing well. If you're writing "and" in the description, split it. A gate-decision skill evaluates signals — it doesn't collect them, fix issues, or manage the merge.

### 2. Prefer Decomposition

Break large workflows into smaller, focused units. Each piece is independently testable, reusable, and maintainable.

**When NOT to decompose:** Logic is truly one-off (no reuse), overhead exceeds benefit (< 10 lines), or tight coupling makes separation artificial.

### 3. Size Limits

| Type | Target | Max | Signal |
|------|--------|-----|--------|
| Command (simple) | 50-80 | 100 | Doing too much |
| Command (orchestrator) | 80-120 | 150 | Decompose into subcommands |
| Skill | 100-200 | 400 | Split into focused skills |
| Agent | 100-150 | 200 | Extract common patterns to a skill |

### 4. Bounded Context

Agents have a defined expertise boundary and a constrained toolset. A QA agent has `Read, Grep, Glob` — deliberately no `Write` or `Edit` — because QA verifies, it doesn't fix. Tool constraints enforce role boundaries.

### 5. Reference, Don't Repeat

If logic exists in another component, delegate to it. Never copy-paste between skills, commands, or agents. One source of truth per concept.

### 6. Explicit Contracts

Document what each component reads, writes, and expects. No hidden state, no implicit dependencies. Every handoff between components is through the filesystem or explicit arguments.

---

## Documentation Standards

### Frontmatter

**Skills:**
```yaml
---
name: lowercase-hyphens          # Required, max 64 chars
description: What and when        # Required -- triggers auto-invocation
argument-hint: [arg1] [arg2]      # Optional: shown in autocomplete
disable-model-invocation: true    # Optional: user-only (for side-effect workflows)
user-invocable: false             # Optional: background-only knowledge
allowed-tools: Read, Grep         # Optional: restrict tool access
model: claude-opus                # Optional: override model
context: fork                     # Optional: run in subagent
agent: Explore                    # Optional: subagent type
---
```

**Agents:**
```yaml
---
name: lowercase-hyphens           # Required
description: Role and when        # Required -- triggers proactive use
tools: Read, Write, Edit, Bash    # Required -- tool allowlist (enforces bounded context)
model: opus                       # Required -- opus for reasoning, haiku for operations
color: green                      # Required -- terminal display color
---
```

**Commands:** No frontmatter. The title and section structure carry the contract.

### Naming Conventions

| Type | Convention | Pattern | Examples |
|------|-----------|---------|----------|
| Skill | Noun or noun-phrase | `<domain>-<concept>` | `gate-decision`, `security-review`, `composition-patterns` |
| Command | Verb or verb-phrase | `<action>` or `<action>-<target>` | `push`, `verify`, `collect-signals`, `sprint-run` |
| Agent | Role name | `<role>` or `<role>-<specialty>` | `architect`, `tdd-guide`, `code-reviewer`, `qa-agent` |

All names: lowercase, hyphens only, max 64 characters.

### Structure Templates

**Skills** open with a directive, then organize by criteria:
```text
**You are [doing what].** [Use this to...]
## When to Use
## [Core content -- criteria, methodology, patterns]
## Output [format if applicable]
```

**Commands** open with purpose, then organize by workflow:
```text
# [Name]
[1-2 sentence purpose]
## Usage
## Instructions [step-by-step]
## Error Handling
## Arguments
## Composition / Used By
```

**Agents** open with persona, then organize by methodology:
```text
You are a [role] who [mission].
## Your Role
## [Methodology -- how you work]
## [Checklists / Criteria]
## Output Format
```

### Voice

- **Skills:** Directive — "**You are making a ship/no-ship decision.** Read the review files..."
- **Commands:** Imperative — "Run the full CI validation suite locally before pushing."
- **Agents:** Second-person persona — "You are a senior code reviewer ensuring high standards..."

---

## File Organization

```text
skills/<name>/
  SKILL.md             # Main instructions (required)
  templates/           # Output templates (optional)
  examples/            # Example outputs (optional)
  scripts/             # Supporting scripts (optional)

commands/<name>.md     # Single file per command

agents/<name>.md       # Single file per agent
```

Supporting files (templates, examples, scripts) live **inside the skill directory**, not alongside commands or agents. If a command needs templates, create a companion skill to hold them.

**Sprint-specific templates:** `skills/sprint/templates/` — one YAML template per phase output file.

---

## Composition Rules

How the three types connect:

```text
Commands  --invoke-->   Agents      (for specialized work)
Commands  --apply--->   Skills      (for knowledge/criteria)
Commands  --delegate->  Commands    (for sub-workflows)
Agents    --use----->   Skills      (for reference/guidance)
Skills    --reference-> Skills      (for shared patterns)
```

**Max delegation depth:** 2-3 levels. Deeper nesting is an anti-pattern.

**Pattern catalog:** See `skills/composition-patterns/` for the full set: delegation, pipeline, gate, loop, alias, composition, fallback, decorator, and handoff protocol patterns.

**Handoff protocol:** For multi-phase pipelines with persistent state (like the sprint lifecycle), use the handoff protocol pattern. Each phase reads the previous handoff from the filesystem, does its work, and writes its own handoff. See `skills/composition-patterns/` for the standard envelope fields.

---

## Anti-Patterns

- **Monolithic commands** (> 150 lines) — decompose into command + delegated sub-commands
- **Deep nesting** (> 3 delegation levels) — flatten the hierarchy
- **Circular delegation** (A calls B calls A) — never; redesign the boundary
- **Hidden side effects** — document everything a component reads, writes, and modifies
- **Implicit contracts** — be explicit about expected inputs, outputs, and state
- **Duplicated logic** — if you copy-paste between components, extract to a shared skill
- **Unbounded agents** — always define the tool allowlist; tool constraints enforce role scope
- **Skills that execute** — if it has side effects, it's a command, not a skill
- **Agents called directly by users** — agents are invoked by commands; users invoke commands
- **Role bleed** — a reviewer doesn't fix code; a QA engineer doesn't make design decisions; respect professional boundaries
