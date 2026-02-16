---
name: testing-strategy
description: Decision framework for choosing testing methods. Use when starting a new test suite, evaluating test quality, or deciding between TDD schools, property-based testing, mutation testing, or BDD.
argument-hint: [module-or-context]
---

# Testing Strategy Decision Framework

**You are choosing a testing approach.** Apply this framework to select the right method for the code under test, then delegate execution to `/tdd-workflow`.

## Quick Decision Table

| Situation | Primary Method | Supplement With |
|-----------|---------------|-----------------|
| Domain logic, value objects, pure functions | Chicago TDD | Property-based |
| Complex collaborator graphs, ports/adapters | London TDD (boundaries only) | Chicago for core |
| Serialization, parsing, encoding | Chicago TDD | Property-based (roundtrip) |
| Authorization, financial calc, data integrity | Chicago TDD | Mutation testing audit |
| Business rules shared with non-developers | BDD Gherkin | Chicago for internals |
| Complex domain with aggregates, invariants | Chicago TDD | DDD modeling (tactical patterns) |
| CRUD endpoints, glue code | Chicago TDD | (nothing extra) |
| Algorithm with wide input space | Chicago TDD | Property-based (invariants) |
| Legacy code with unknown coverage quality | (existing tests) | Mutation testing audit |

## Master Decision Tree

```
START: What are you testing?
│
├─► Pure domain logic (calculations, rules, transformations)
│   ├─ Chicago TDD as primary method
│   ├─ Property-based tests for functions with wide input spaces
│   └─ Mutation testing audit if this is critical-path code
│
├─► Adapter / integration boundary (DB, HTTP, queues, APIs)
│   ├─ London TDD for the adapter itself (mock the external)
│   ├─ Integration tests with real infrastructure (test containers)
│   └─ Do NOT property-test I/O boundaries
│
├─► API endpoints / controllers
│   ├─ Integration tests with test client (Chicago style)
│   ├─ Cover: happy path, 400, 401, 403, 404, 500
│   └─ Mock only external services, not your own code
│
├─► Complex business rules shared with stakeholders
│   ├─ Do non-devs actually collaborate on specs?
│   │   ├─ Yes → BDD Gherkin for acceptance tests
│   │   │         Chicago TDD for internal implementation
│   │   └─ No  → Chicago TDD with Given/When/Then comments
│   └─ Property-based tests if rules have combinatorial inputs
│
├─► Complex domain with business invariants
│   ├─ Are aggregate boundaries unclear or contested?
│   │   └─ YES → Consult DDD modeling guide (methods/ddd-modeling.md)
│   ├─ Chicago TDD for entities, aggregates, domain services
│   ├─ Property-based tests for value objects
│   └─ London TDD for anti-corruption layers
│
├─► Encoding / parsing / serialization
│   ├─ Chicago TDD for examples
│   └─ Property-based roundtrip tests (always)
│
├─► Legacy code with unknown test quality
│   ├─ Run mutation testing to find blind spots
│   ├─ Fix critical survivors first
│   └─ Then apply Chicago TDD going forward
│
└─► CRUD / config / glue / boilerplate
    ├─ Chicago TDD integration tests
    ├─ Don't over-invest — low defect risk
    └─ Skip property-based, mutation, and Gherkin
```

## The Five Methods (Summary)

### Chicago TDD — The Default

Test *behavior*, not structure. Use real collaborators. Mock only at architectural boundaries.

**Why default:** Tests survive refactoring. Read like specifications. Cheapest over time.
**Tradeoff:** Harder failure isolation. Slower design feedback on interfaces.

See: `methods/chicago-vs-london.md`

### London TDD — At Boundaries Only

Mock collaborators. Test one class in isolation. Outside-in development.

**Why use it:** Verifying interaction protocols. Driving interface discovery. Deep dependency chains.
**Tradeoff:** Tests mirror implementation. False confidence from happy-path mocks. Refactoring paralysis.

See: `methods/chicago-vs-london.md`

### Property-Based Testing — For Invariants

Declare universal properties. Framework generates hundreds of inputs to violate them.

**Why use it:** Catches edge cases humans miss. Forces formal reasoning about correctness.
**Tradeoff:** Properties are hard to write well. Generator investment for custom types. Slower execution.

See: `methods/property-based.md`

### Mutation Testing — For Auditing

Inject faults. Check if tests catch them. Survivors reveal weak assertions.

**Why use it:** Exposes coverage theater. Finds assertion gaps. Educational for teams.
**Tradeoff:** 10-50x runtime cost. Equivalent mutant noise. Diminishing returns past ~85%.

See: `methods/mutation-testing.md`

### BDD Gherkin — For Cross-Role Collaboration

Human-readable scenarios driving automated tests. Given/When/Then syntax.

**Why use it:** Shared language with non-devs. Auditable acceptance criteria. Domain documentation.
**Tradeoff:** Step definition maintenance burden. Only valuable if non-devs actually participate.

See: `methods/bdd-gherkin.md`

### DDD Modeling — For Complex Domains

Structure code around business reality using aggregates, value objects, entities, and bounded contexts.

**Why use it:** Prevents modeling errors in complex domains. Enforces consistency boundaries. Non-obvious rules that Claude won't infer.
**Tradeoff:** Upfront investment. Overkill for CRUD or simple domains. Requires domain expert access for full benefit.

See: `methods/ddd-modeling.md`

## The Hybrid Rule (Architecture Layer Map)

```
                ┌─────────────────────────────┐
                │       API / Controller       │  ← Integration tests
                │         (thin layer)         │    (real HTTP, test client)
                ├─────────────────────────────┤
                │       Service / Domain       │  ← Chicago TDD
                │    (business logic lives)    │    (real objects, real behavior)
                ├─────────────────────────────┤
                │     Adapters / Ports         │  ← London TDD
                │   (DB, HTTP, queues, APIs)   │    (mock the external system)
                └─────────────────────────────┘
```

**Rule of thumb:** If the collaborator is *yours* (you wrote it, you control it), use the real thing. If it's *theirs* (external API, database, message broker), mock it.

## Method Compatibility Matrix

| | Chicago | London | Property | Mutation | Gherkin | DDD |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Chicago** | - | Hybrid at boundaries | Supplement | Audit | Acceptance layer | Aggregates/entities |
| **London** | Hybrid at core | - | Rare | Audit | Acceptance layer | ACL/adapters |
| **Property** | Supplement | Rare | - | Audit generators | No | Value objects |
| **Mutation** | Validates | Validates | Validates | - | Validates | Validates |
| **Gherkin** | Internals | Internals | No | Audit steps | - | Ubiquitous language |
| **DDD** | Primary method | Boundaries | Value objects | Audit | Scenarios | - |

## Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|-------------|---------|-----|
| **Mock-heavy tests** | Tests break on every refactor | Switch to Chicago; mock only boundaries |
| **Test-per-method** | Tests mirror class structure 1:1 | Test behaviors, not methods |
| **100% coverage theater** | High coverage, low confidence | Mutation testing to find weak assertions |
| **Gherkin with no audience** | Only devs read feature files | Drop Gherkin, use structured pytest |
| **Property tests restating code** | `assert f(x) == (x * 2 + 1)` | Test properties, not implementations |
| **Testing implementation** | `assert mock.called_with(x)` on internals | Assert on observable outputs and state |
| **Mutation chasing** | Trying to kill every mutant | Accept ~85%; ignore equivalent mutants |

## Composition

```
/testing-strategy (this skill)
    │
    ├── Decides approach → then delegates to:
    │
    ├── /tdd-workflow          ← Executes the chosen TDD school
    ├── standards/testing_standards.md  ← Structural requirements
    └── standards/TEST_NAMING.md       ← Naming conventions
```

This skill informs the *strategy*. `/tdd-workflow` executes the *process*. Testing standards enforce the *structure*.
