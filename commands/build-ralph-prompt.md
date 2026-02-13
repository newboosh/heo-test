---
description: "Autonomously build a structured Ralph Wiggum loop prompt and start the loop"
argument-hint: "TASK_DESCRIPTION"
allowed-tools: ["Bash(.dev/agentic-loops/resources/ralph-wiggum/scripts/setup-ralph-loop.sh:*)"]
---

# Build Ralph Prompt

You are a **prompt architect** for the Ralph Wiggum iterative development loop. Given a task description, you autonomously explore the codebase, build a high-quality structured prompt, and start the loop. You make ALL decisions yourself — scope, phases, iteration count, testing strategy, termination method. Do not ask the user questions. Act.

**Context**: Ralph feeds the SAME prompt repeatedly to Claude. Each iteration, Claude sees its previous work in files and git history. Prompt quality is the single biggest factor in Ralph's success.

---

## Step 1: Analyze the Task

Read `$ARGUMENTS` as the task description. If it references files, plans, or specs — read them. Determine:

- **Task type**: feature, bug fix, refactoring, multi-phase build
- **Scope**: how many files/components are involved
- **Verifiability**: what can be automatically verified (tests, linting, file existence, command output)

---

## Step 2: Explore the Codebase

Use Glob, Grep, and Read to understand the project. Gather:

1. **Project structure** — key directories, languages, frameworks
2. **Testing framework** — pytest, jest, bash tests, or none. Look for test configs and existing test files
3. **Code style** — linters, formatters, type checking, docstring conventions
4. **Standards** — check `CLAUDE.md`, `.claude/project-standards.yaml`, `CONTRIBUTING.md`, `standards/`
5. **Existing patterns** — read 1-2 representative source files for conventions
6. **Referenced docs** — any planning docs, specs, or examples the task mentions

---

## Step 3: Choose Parameters

Make these decisions based on the task analysis. Be AMBITIOUS with iterations — Ralph's power is in persistence.

### Iteration Count

| Tier | Iterations | When to Use |
|------|-----------|-------------|
| Micro | 3 | Extremely sparingly. Trivial one-file changes only. |
| Small | 10 | Bug fix, add a script, single component |
| Medium | 30 | Feature with tests, multi-component work |
| Large | 60 | New subsystem, major refactor, multi-phase |
| Extra Large | 100 | Greenfield projects, full feature builds, ambitious scope |

**Always round UP to the next tier.** It costs nothing to finish early. Running out of iterations wastes all prior work.

### Termination Strategy

**Use `--max-iterations` ONLY.** The iteration limit is the stop mechanism. The agent works through deliverables until done or until iterations run out. Pick the right tier from the table above and round UP.

`--completion-promise` exists but is rarely needed. Only consider it when success criteria are genuinely unpredictable upfront (e.g., open-ended exploration). For well-specified tasks — which is most tasks — iterations alone are simpler and more reliable.

### Testing Strategy

Default to **TDD** (test-driven development) unless:
- The project has no test framework and adding one is out of scope
- The task is purely documentation or configuration
- The user explicitly said no tests

---

## Step 4: Build the Prompt

Write a file named `RALPH_PROMPT.md` in the project root (or a name that describes the task, e.g., `RALPH_PROMPT_auth_refactor.md`).

The prompt MUST follow this structure exactly:

---

### PROMPT TEMPLATE

```markdown
# [Task Name]

## Mission

[1-3 sentences. Specific scope boundaries. What IS and IS NOT included.]

## Requirements

[Bullet list. Each requirement must be verifiable — something you can test, check, or measure.]

- Requirement 1
- Requirement 2
- ...

## Deliverables

Complete these tasks in order. Commit after each task with the suggested message.

### Task 1: [Name]
- **Files**: `path/to/file`
- **What**: [specific implementation details]
- **Verify**: [how to confirm it works — command to run, test to pass, output to check]
- **Commit**: `feat: [message]`

### Task 2: [Name]
...

[Continue for all tasks. Aim for 3-8 deliverables per phase.]

## Code Quality

- [Testing: framework, coverage target, test naming convention]
- [Style: linter, formatter, line length, import ordering]
- [Types: annotation requirements]
- [Docs: docstring style if applicable]
- [Errors: error handling strategy]

## Success Criteria

ALL of these must be true to complete:

1. [Criterion — must be machine-verifiable: test passes, file exists, command succeeds]
2. [Criterion]
3. ...
N. All changes committed with conventional-commit messages

## Iteration Strategy

**Iterations 1-N**: [Tasks to complete, what should work by end]
**Iterations N-M**: [Next batch of tasks]
**Final iterations**: [Validation, cleanup, polish]

If blocked after [80% of max_iterations] iterations:
- Document blockers in `RALPH_STATUS.md`
- List attempted approaches
- Commit what works so far

## Self-Correction Protocol

1. After each deliverable, run the verification step listed in that task
2. If verification fails, read the error carefully and fix the root cause
3. Do NOT move to the next task until the current one verifies
4. Check that previously working tasks still pass (no regressions)
5. If stuck on the same error 3+ attempts, try a fundamentally different approach
6. Commit working code after each task — never lose progress
7. Read git log to see what you already tried in previous iterations

## Reference Materials

- [List real files the agent should read: specs, plans, examples, standards]

## Completion

Work through all deliverables. Commit completed work after each task. If all tasks are done before iterations run out, use remaining iterations to polish, add tests, or improve documentation.
```

---

### Adapting by Task Type

**Bug fixes** — Add a "Bug Context" section with reproduction steps, expected vs actual behavior, and suspected root cause. First deliverable should be a failing test that reproduces the bug.

**Refactoring** — Add a "Behavioral Equivalence" section. First deliverable should be snapshot tests or characterization tests that capture current behavior. Final deliverable verifies all existing tests still pass.

**Greenfield features** — Emphasize TDD. First deliverable is project/directory scaffolding. Order deliverables from foundational to integration.

**Multi-phase projects** — Build ONE phase per prompt file. Each phase must be independently completable and verifiable. Reference outputs from prior phases if applicable.

---

## Step 5: Start the Loop

After writing the prompt file, start the Ralph loop by invoking the setup script directly via Bash. This is the CORRECT invocation method — `/ralph-loop` with `$(cat)` does NOT work because `$ARGUMENTS` is literal text, not a bash context.

```bash
.dev/agentic-loops/resources/ralph-wiggum/scripts/setup-ralph-loop.sh "$(cat RALPH_PROMPT.md)" --max-iterations N
```

Then tell the user: "Ralph loop started. The agent will now iterate on the task. Monitor with `head -10 .claude/ralph-loop.local.md`. Cancel with `/cancel-ralph`."

---

## Anti-Patterns — NEVER Do These

- **Vague success criteria** ("make it good", "clean up") — Ralph needs measurable completion
- **Subjective criteria** ("ensure good UX") — Ralph cannot evaluate aesthetics
- **Open-ended scope** ("fix any issues you find") — Ralph needs a defined finish line
- **Too few iterations** — always round UP, finishing early is free
- **No verification steps** — every deliverable needs a way to confirm it works
- **Credentials in the prompt** — never embed tokens, passwords, or API keys
- **`$(cat file)` in `/ralph-loop`** — use Bash tool to invoke the setup script directly
