# Context (Context Preparation)

Explicitly invoke the Context Agent to prepare comprehensive context before starting work.

## Usage

```
/context <task description>
```

## When to Use

The Context Agent activates **proactively** before coding tasks. Use `/context` to:
- Explicitly request a full context briefing
- Re-gather context after requirements change
- Get context for a specific subtask
- Understand how a task fits into the bigger picture

## Context Gathered

| Source | Information |
|--------|-------------|
| **Plan** | Current implementation plan, phase, steps |
| **Todo List** | Related tasks, blockers, dependencies |
| **Meta-Plan** | Project goals, roadmap, architectural direction |
| **Processes** | Affected business processes, workflows |
| **Data Structures** | Models, schemas, data flow |
| **Standards** | Applicable coding standards |
| **Prior Art** | Similar implementations in codebase |

## Skills & Agents Composed

```text
/context "Add refund capability to payment service"
    │
    ├─► plan-context      → Current plan, meta-plan, roadmap
    ├─► TaskList          → Related tasks, blockers
    │
    ├─► Explore agent     → Deep dive: payment code, dependencies
    ├─► librarian find    → Locate payment-related files
    │
    ├─► process-map       → Payment process flow, affected services
    │                     → Payment model, schemas, data flow
    │
    ├─► standards-lookup  → api_standards, code_style_standards
    ├─► find-patterns     → Similar refund patterns in codebase
    ├─► gather-docs       → Payment docs, API specs
    └─► prereq-check      → Dependencies, test setup
            │
            ▼
      Context Briefing
```

## Output

Context Briefing containing:
- **Plan Context:** Current plan, phase, meta-plan goals
- **Task Context:** Related tasks, blockers, dependencies
- **Affected Processes:** Business processes impacted, upstream/downstream
- **Affected Data:** Models, schemas, data flow
- **Standards:** Applicable standards (per project-standards.yaml)
- **Reference Implementation:** Similar code to follow
- **Prerequisites:** What's needed to start
- **Checklist:** Pre-work verification items

## Examples

```
/context Add refund capability to payment service
/context Implement user notification preferences
/context Create ERD for the order management system
/context Refactor authentication to use JWT
```

Invokes the **context-agent**.

## Error Handling

If context sources are missing, the briefing will indicate:
- **No plan found:** Recommends creating `PLAN.md`
- **No standards match:** Uses defaults, suggests checking work type
- **No similar code:** Notes this may be a new pattern
- **Prerequisites unclear:** Requests explicit task type

See individual skill documentation for detailed empty state handling.
