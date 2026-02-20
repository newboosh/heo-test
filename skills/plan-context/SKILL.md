---
name: plan-context
description: Gather current plan, todo list, and meta-plan context. Used by Context Agent to understand the bigger picture before work begins.
model: opus
allowed-tools: Read, Grep, Glob
---

# Plan Context

Gather planning context to understand where this task fits in the bigger picture.

## Input

- **task**: Description of the work to be done

## Context Sources

### 1. Current Plan

Look for active implementation plans (in order of preference):

```
# Primary locations
Glob: "PLAN.md"
Glob: ".claude/plans/**/*.md"
Glob: "docs/plans/**/*.md"

# Fallbacks
Glob: "**/PLAN.md"
Glob: "**/plan.md"
Glob: "**/implementation-plan.md"

# Last resort: check README for plan sections
Grep: "## (Implementation|Plan|Roadmap)" in README.md
```

**If no plan found:**
```markdown
### Current Plan
- **Status:** No formal plan found
- **Recommendation:** Consider creating `PLAN.md` or `docs/plans/<feature>.md`
- **Alternative:** Check with team for planning documents in external tools
```

Extract (when found):
- Current phase
- Completed steps
- Remaining steps
- Dependencies
- Success criteria

### 2. Todo List

Check the task management system:

```
TaskList → Get all tasks
```

Extract:
- Tasks related to current work
- Blocked tasks
- Blocking tasks
- In-progress tasks
- Task dependencies

### 3. Meta-Plan / Roadmap

Look for higher-level project direction:

```
# Primary locations
Glob: "ROADMAP.md"
Glob: ".claude/meta-plan.md"
Glob: "docs/architecture/**/*.md"

# Fallbacks
Glob: "**/ROADMAP.md"
Glob: "**/META-PLAN.md"
```

Also check:
- ADRs for architectural decisions (`docs/adr/`, `docs/decisions/`)
- README for project goals (look for "## Goals", "## Vision", "## Roadmap")
- CONTRIBUTING for project philosophy
- `package.json` or `pyproject.toml` for project description

**If no meta-plan found:**
```markdown
### Meta-Plan
- **Status:** No formal roadmap found
- **Inferred from README:** [Extract goals section if present]
- **Recommendation:** Consider creating `ROADMAP.md` for project direction
```

## Output

```markdown
## Plan Context

### Current Plan
- **Plan:** `docs/plans/feature-x.md`
- **Phase:** 2 of 4 (Service Layer)
- **Completed:**
  - [x] Database migration
  - [x] Model updates
- **Current Step:** Implement service methods
- **Remaining:**
  - [ ] API endpoints
  - [ ] Tests

### Todo List
- **Related Tasks:**
  - #12: Implement PaymentService (in_progress)
  - #13: Add payment API endpoint (pending, blocked by #12)
- **Blockers:** None
- **This task blocks:** #13, #15

### Meta-Plan
- **Project Goal:** Build payment processing system
- **Architectural Direction:** Microservices, event-driven
- **Current Milestone:** MVP payment flow
- **Key Decisions:**
  - ADR-005: Use Stripe for payments
  - ADR-008: Event sourcing for transactions
```

## Locations Checked

| Source | Locations |
|--------|-----------|
| Plans | `PLAN.md`, `docs/plans/`, `.claude/plans/` |
| Roadmap | `ROADMAP.md`, `docs/architecture/` |
| Meta-plan | `META-PLAN.md`, `.claude/meta-plan.md` |
| ADRs | `docs/adr/`, `docs/decisions/` |
| Tasks | TaskList tool |

## Expected Project Structure

For best results, projects should follow these conventions:

```
project/
├── PLAN.md                    # Current implementation plan
├── ROADMAP.md                 # High-level project direction
├── README.md                  # Project overview (fallback for goals)
├── .claude/
│   ├── plans/                 # Implementation plans
│   │   └── feature-x.md
│   └── meta-plan.md           # Alternative meta-plan location
└── docs/
    ├── plans/                 # Implementation plans
    ├── architecture/          # Architecture docs
    ├── adr/                   # Architecture Decision Records
    └── decisions/             # Alternative ADR location
```

## Usage

**Context Agent:** Gather plan context at the start of context gathering to understand where the task fits in the project.

## Dependencies

This skill is standalone but works best when projects follow the expected structure above.
