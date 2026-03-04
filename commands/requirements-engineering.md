---
description: Formal requirements analysis (IEEE 29148)
help-usage: '`/requirements-engineering <problem statement or feature name>`'
---

# Requirements Engineering

Structured requirements elicitation, analysis, specification, and validation
following IEEE 29148:2018. Takes a **defined problem** and produces formal,
testable requirements with full traceability.

## Usage

```
/requirements-engineering <problem statement or feature name>
```

## When to Use

- A defined problem exists (from `/problem-definition` or user-provided)
- Stakeholder needs must be documented and translated into specifications
- Requirements need validation against IEEE 29148 quality characteristics
- Traceability from needs to verification is required

## Input Detection

| Input available | What happens |
|----------------|-------------|
| `.problem-definition/handoff.yaml` | Imports problem owners, gap analysis, solution space mechanically. Highest quality. |
| `.problem-definition/problem-definition.md` | Parses problem context semantically. High quality. |
| User-provided problem statement | Validates the statement, asks clarifying questions if vague. |
| Just a feature name | Runs lightweight discovery (3-5 questions) before proceeding. |

## Process

```text
/requirements-engineering "Task management API for teams"
    │
    ├─► Process 1: Stakeholder Needs & Requirements (IEEE 29148 §6.2)
    │   ├─► Step 1.1: Identify stakeholders
    │   ├─► Step 1.2: Elicit stakeholder needs
    │   ├─► Step 1.3: Resolve conflicts
    │   └─► Step 1.4: Write stakeholder requirements
    │
    └─► Process 2: System Requirements (IEEE 29148 §6.3)
        ├─► Step 2.1: Derive system requirements (functional + non-functional)
        ├─► Step 2.2: Validate the requirements set
        └─► Step 2.3: Build traceability matrix
```

## Output

A requirements specification with:
- Stakeholder analysis and needs
- Formal requirements (each passing IEEE 29148 quality checks)
- Functional and non-functional system requirements
- Traceability matrix (needs → stakeholder reqs → system reqs → verification)

## Integration

Before requirements engineering:
- Use `/problem-definition` to define the problem clearly
- Use `/boundary-critique` to challenge framing assumptions

After requirements engineering:
- Use `/plan` to create an implementation plan
- Use `/tdd` to implement with test-driven development

Uses the **requirements-engineering** skill internally.
