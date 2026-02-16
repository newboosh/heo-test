---
name: bug-investigate
description: Hypothesis-driven bug investigation with evidence provenance. Use when debugging non-trivial bugs that resist a quick fix, or when a fix attempt has already failed once. Enforces problem-definition-first, single-variable testing, and prevention sweep.
argument-hint: [bug description or error message]
---

# Bug Investigation Skill

**You are investigating a bug systematically.** Do not attempt fixes until you have completed the Problem Definition phase. Every investigation step tests exactly one hypothesis.

## Philosophy

Debugging fails in two predictable ways: (1) jumping to a fix before understanding the problem, and (2) making multiple changes at once so you cannot attribute what helped. This skill prevents both by requiring a written problem statement before any code changes, and a hypothesis ledger where each entry tests exactly one variable.

This is the scientific method applied to code: observe, hypothesize, test, record.

## When to Use

- Bug resists a quick fix (you or Claude already tried once and failed)
- Behavior is intermittent or environment-dependent
- Multiple possible root causes exist
- User report contradicts what the code appears to do
- You need to hand off investigation context to another session

**When NOT to use:**
- Build/type errors with clear messages -- delegate to `build-error-resolver` agent
- Failing tests with obvious assertion mismatches -- just fix them
- Lint/format errors -- delegate to `/build-fix` or `/verify`

## Phase 0: Detect Toolchain

Before investigating, identify the project's language and verification tools. Check in this order:

| Indicator File | Language | Verification Command |
|---|---|---|
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python | `pytest`, `mypy`, `ruff` |
| `package.json` | JS/TS | `npm test`, `npx tsc --noEmit`, `npx eslint .` |
| `go.mod` | Go | `go test ./...`, `go vet ./...` |
| `Cargo.toml` | Rust | `cargo test`, `cargo clippy` |
| `pom.xml`, `build.gradle` | Java/Kotlin | `mvn test`, `gradle test` |
| `Gemfile` | Ruby | `bundle exec rspec`, `rubocop` |
| `*.csproj`, `*.sln` | C#/.NET | `dotnet test`, `dotnet build` |
| `Makefile` | Any | Check `make test`, `make check` targets |

Also check for project-specific test scripts:
```
Glob: "Makefile"
Glob: "justfile"
Glob: "scripts/test*"
Glob: ".github/workflows/*.yml"   # CI config reveals the real verification commands
```

Store the detected toolchain. Use it for all verification steps below.

**For Python projects:** Prefer delegating build/type errors to `build-error-resolver` agent and using `/verify` for quality gates. This skill handles the investigation logic; those handle the mechanical fixing.

## Phase 1: Problem Definition (MANDATORY -- Do Not Skip)

Before touching any code, produce this block in your response:

```
PROBLEM DEFINITION
==================
Symptom:       <What is observed? Quote exact error messages or describe exact behavior.>
Expected:      <What should happen instead?>
Scope:         <Where does this occur? Which files, endpoints, functions, environments?>
Reproducer:    <Exact steps or command to trigger the bug. If unknown, say "unknown".>
First seen:    <When? After which change? If unknown, say "unknown".>
Already tried: <What has been attempted? What was the result?>
```

**Rules:**
- "Symptom" must quote verbatim error text or describe observable behavior, not your interpretation.
- "Expected" must describe the correct behavior, not just "it should work."
- If the user gave a vague description, ask clarifying questions before proceeding. Do not guess.

## Phase 2: Evidence Collection

Gather evidence from multiple sources. Tag each piece with its authority level:

### Evidence Authority Levels

| Level | Source | Weight | Reasoning |
|---|---|---|---|
| **A -- Definitive** | Reproducer output, stack trace, failing test | Highest | Machine-generated, exact, current |
| **B -- Strong** | Error logs with timestamps, git blame/diff | High | Machine-generated but may be stale or incomplete |
| **C -- Contextual** | Source code reading, documentation | Medium | Requires interpretation; code may not match runtime |
| **D -- Anecdotal** | User report, "it worked yesterday", verbal description | Low | Human memory is unreliable; may omit key details |

**Collection protocol:**

1. **Try to reproduce** (get Level A evidence):
   - Run the reproducer from the Problem Definition
   - If no reproducer exists, construct one from the symptom description
   - Capture full output (stdout, stderr, exit code)

2. **Read the stack trace / error output** (Level A):
   - Identify the exception type and message
   - Note every file:line in the trace that belongs to this project (ignore stdlib/vendor)
   - Identify the innermost project frame -- this is where investigation starts

3. **Check recent changes** (Level B):
   ```
   git log --oneline -20
   git diff <baseline>.. -- <files from stack trace>
   ```
   Use the "First seen" field from Phase 1 to pick `<baseline>`. If unknown, start with `HEAD~5` and widen if nothing relevant appears.

4. **Read the code at fault** (Level C):
   - Read 30 lines around each project frame in the stack trace
   - Note assumptions the code makes about inputs, state, environment

5. **Check logs** (Level B):
   - Search for relevant log entries around the timestamp of the failure

Record evidence with provenance tags:

```
EVIDENCE LEDGER
===============
[A] pytest output: "AssertionError: expected 200, got 500" (tests/test_api.py:42)
[A] Stack trace: KeyError in app/services/user.py:88 -- accessing dict['email'] on None
[B] git log: user.py last changed in commit abc123 "refactor: extract user service" (2 days ago)
[C] Code reading: get_user() returns Optional[User] but caller does not check for None
[D] User report: "it worked fine last week"
```

## Phase 3: Hypothesize and Test

For each hypothesis, follow this exact structure:

```
HYPOTHESIS #N
=============
Claim:    <One specific, falsifiable statement about the root cause.>
Based on: <Reference evidence ledger entries by tag, e.g., "[A] stack trace + [C] code reading">
Test:     <Exactly one action that will confirm or refute this hypothesis.>
Predicts: <What you expect to observe if the hypothesis is correct.>
```

Then execute the test. Record the result:

```
RESULT #N
=========
Outcome:  CONFIRMED | REFUTED | INCONCLUSIVE
Observed: <What actually happened.>
Next:     <If confirmed: proceed to fix. If refuted: next hypothesis. If inconclusive: what additional evidence is needed.>
```

**Rules:**
- Test exactly ONE variable per hypothesis. Do not change two things at once.
- Maximum 5 hypotheses before reassessing. If 5 hypotheses are all refuted, return to Phase 1 and re-examine whether the Problem Definition is correct.
- If a hypothesis requires a code change to test, make it on a throwaway branch or revert it immediately after testing.

## Phase 4: Fix

Once a hypothesis is confirmed:

1. **State the root cause** in one sentence referencing evidence.
2. **Apply the minimal fix** -- change the fewest lines possible to correct the root cause.
3. **Verify the fix:**
   - Re-run the reproducer from Phase 1
   - Run the project's test suite (using the toolchain detected in Phase 0)
   - Confirm no new failures introduced
4. **Show the diff** -- present the exact changes made.

**Delegation rules (Python projects):**
- If the fix is a type/lint error: delegate to `build-error-resolver` agent
- If the fix requires running a verification loop: delegate to `/verify`
- If the fix involves test creation: delegate to `/tdd-workflow`

**All other languages:** Run the verification commands detected in Phase 0. If the project has a CI configuration, mirror what CI runs.

## Phase 5: Prevention Sweep (MANDATORY -- Do Not Skip)

After fixing, search for the same pattern class elsewhere in the codebase.

**Use the `find-patterns` skill** or direct Grep searches:

```
Grep: <pattern that matches the same mistake>
```

Examples:
- Bug was unchecked None: search for other callers of the same function that skip None checks
- Bug was missing error handling: search for other call sites of the same external API
- Bug was wrong type assumption: search for similar type casts or conversions
- Bug was race condition: search for similar shared-state access patterns

**Report:**

```
PREVENTION SWEEP
================
Pattern searched: <what you searched for>
Matches found:    <count>
At risk:
  - file.py:123 -- same unchecked Optional return
  - other.py:456 -- similar pattern, but has guard clause (safe)
Action: <fix now | create issue | note for review>
```

If matches represent the same bug class, either fix them now (if small and safe) or note them for follow-up.

## Phase 6: Bug Report (Output)

Produce this summary at the end of every investigation:

```
BUG REPORT
==========
ID:            <descriptive slug, e.g., "unchecked-none-user-service">
Root Cause:    <One sentence.>
Evidence:      <Key ledger entries that proved it, with authority tags.>
Fix:           <One sentence describing what was changed.>
Files Changed: <list>
Verified By:   <What commands confirmed the fix.>
Prevention:    <How many similar patterns found. How many fixed.>
Learned:       <One sentence: what principle was violated? What should be checked in future?>
```

**Integration with continuous-learning:** If the "Learned" insight is reusable, consider saving it via `/learn` for future sessions.

## What This Skill Does NOT Do

- **Does not replace language-specific tools.** It orchestrates investigation; it delegates mechanical fixing to `build-error-resolver`, `/verify`, `/build-fix`, and `/tdd-workflow`.
- **Does not handle build errors.** Build errors with clear messages (type errors, lint failures, missing imports) should go directly to `/build-fix`. This skill is for bugs where the code runs but behaves incorrectly, or where the error cause is non-obvious.
- **Does not do speculative patching.** If you cannot reproduce the bug and have no Level A or B evidence, escalate to the user rather than guessing.
- **Does not maintain a persistent bug database.** Each investigation is self-contained. Use `/learn` to extract reusable patterns.

## Composition

```
bug-investigate (this skill)
    |
    +-- Phase 0: Reads project files (Glob) to detect toolchain
    +-- Phase 2: Uses Bash (read-only) for reproduction, git log, test runs
    +-- Phase 4: Delegates to:
    |   +-- build-error-resolver agent (Python type/lint fixes)
    |   +-- /verify (quality gate after fix)
    |   +-- /tdd-workflow (if regression test needed)
    +-- Phase 5: Uses find-patterns skill for prevention sweep
    +-- Phase 6: Optionally feeds continuous-learning skill via /learn
```
