---
name: team-patterns
description: Reusable coordination patterns for Claude Code Agent Teams. Reference when building team-based commands (review-swarm, bug-swarm, arch-debate, test-swarm, health-check, plan-swarm).
---

# Team Coordination Patterns

**You are building a command that orchestrates an Agent Team.** Apply these patterns for consistent, safe team coordination across all swarm commands.

## Pattern 1: Team Lifecycle

Every team command follows this sequence:

```
0. Initialize    → Determine scope, read sprint state if applicable
1. TeamCreate    → Create team with descriptive name
2. Spawn         → All teammates in a single parallel message (Task calls with team_name)
3. Tasks         → TaskCreate for each work unit, set blockedBy dependencies
4. Work          → Teammates execute, messaging each other as needed
5. Synthesize    → Lead reads all outputs, produces unified deliverable
6. Validate      → Run validators (e.g., scripts.sprint.validate)
7. Shutdown      → SendMessage(type: shutdown_request) to each teammate
8. Cleanup       → TeamDelete
```

**Critical:** Steps 7 and 8 must happen even if step 5 or 6 fails. Use error handling to ensure cleanup.

## Pattern 2: File Ownership Protocol

**No file is written by more than one teammate.** Enforce in every team command.

### Rules
1. Each teammate's spawn prompt includes an explicit **write boundary**: the files they may create or modify
2. Working files go in a team-specific subdirectory (e.g., `.sprint/swarm/`, `.bugswarm/`, `.health/`)
3. The lead owns all **handoff files** (final outputs consumed by downstream phases)
4. Shared files (e.g., `tests/conftest.py`) are owned by the lead, who serializes access via message requests

### Enforcement Template (include in spawn prompts)
```
WRITE BOUNDARY: You may ONLY write to: {file_list}
Do NOT write to any other file. If you need a shared resource modified,
message the lead with a structured request.
```

## Pattern 3: Context Agent Integration

Context Agent is a **permanent teammate** in every team. Standard integration:

```
1. Spawn context-agent first (or in parallel with others)
2. Context Agent gathers via its standard workflow (triage → parallel batch → assembly)
3. Context Agent broadcasts SUMMARY to all teammates (SendMessage type: broadcast)
4. Teammates start work after receiving briefing (use blockedBy on context task)
5. Context Agent remains alive for CONTEXT_REQUEST messages throughout
```

### Message Conventions
- **Request:** `CONTEXT_REQUEST: <what is needed>`
- **Response:** `CONTEXT_RESPONSE: <targeted information>`
- **Briefing:** `CONTEXT_BRIEFING: <structured summary>`

## Pattern 4: Cross-Reference Window

After independent work completes, open a time-boxed collaboration phase:

```
1. Lead broadcasts: "Cross-reference window open. Review each other's findings."
2. Teammates read peers' output files (read access is unrestricted)
3. Teammates exchange messages: CHALLENGE, ESCALATE, CROSS-REF, CONCUR
4. Each teammate updates their own output file with any changes
5. Lead waits for all teammates to signal "done" (TaskUpdate status: completed)
```

**When to use:** Review Swarm, Health Check (cross-concern correlation). Not needed for teams where teammates don't review each other's work (Test Swarm, Plan Swarm).

## Pattern 5: Challenge/Response Protocol

When one teammate disputes another's finding:

```
Challenger → target: "CHALLENGE: [finding ref] — [evidence-based objection]"
Target evaluates and responds:
  → "ACCEPTED: Downgraded to [severity]" (updates own file)
  → "REJECTED: Maintaining because [evidence]"
If unresolved after one exchange:
  → Both positions recorded as "DISPUTED — lead adjudicates"
  → Lead resolves during synthesis using evidence quality
```

**Evidence quality hierarchy (for tiebreaking):**
- Level A: Reproducer output, stack trace, test failure — highest
- Level B: Logs, git blame, metrics
- Level C: Code reading, pattern analysis
- Level D: Inference, heuristic — lowest

## Pattern 6: Convergence Protocol

For teams testing competing hypotheses (Bug Swarm, Arch Debate):

```
EARLY CONVERGENCE:
  One result CONFIRMED + peer supporting evidence → done

ALL REFUTED:
  Lead generates new hypotheses → max 2 rounds → then halt with partial results

CONFLICTING CONFIRMATIONS:
  Evidence quality tiebreaker (Level A > B > C > D)
  If tied: request neutral prediction test
  If still tied: compound finding (both are real)

TIMEOUT:
  Max iterations exhausted → synthesize strongest partial evidence
  Report with confidence: low
```

## Pattern 7: Spawn Specifications

### Model Selection
| Role | Model | Rationale |
|------|-------|-----------|
| Context Agent | opus | Reasoning-heavy synthesis and cross-reference |
| Reviewers / Investigators / Architects | opus | Deep analysis, evidence evaluation |
| Test writers (unit/integration) | opus | Edge case identification, TDD methodology |
| E2E writer | haiku | Follows established POM patterns, less reasoning |
| Coverage monitor | haiku | Operational — runs commands, parses output |
| Health check specialists | sonnet | Tool-running + structured output, moderate reasoning |

### Spawn Prompt Template
```
You are {role_name} in the {team_name} team.

## Your Task
{task_description}

## Your Write Boundary
{exclusive_file_list}

## Agent Methodology
Apply the methodology from: {agent_or_skill_reference}

## Team Communication
- Message teammates using SendMessage for: {message_types}
- Context requests go to teammate "ctx"
- Mark your task complete via TaskUpdate when done
```

## Pattern 8: Error Handling

| Scenario | Standard Response |
|----------|------------------|
| **Teammate fails/times out** | Lead retries once by spawning replacement. If retry fails, lead performs that work dimension (degraded). |
| **Invalid output (bad YAML)** | Lead fixes during synthesis (lead owns final files). |
| **Unresolved dispute** | Both positions recorded as DISPUTED. Lead adjudicates using evidence quality. |
| **Context Agent unavailable** | Teammates proceed with direct file reading. Lead notes "context unavailable." |
| **All teammates fail** | Lead performs work solo. Log degraded mode in output. |
| **Team stuck (no progress)** | Lead broadcasts status check. If still stuck after 1 prompt, shutdown and report partial results. |

## Pattern 9: Sprint Integration

Teams that replace or enhance sprint phases must:

1. **Produce identical handoff files** — same YAML schema, same file paths, passes `python3 -m scripts.sprint.validate`
2. **Update sprint-meta.yaml** — set `current_phase`, log completion in `phase_log`
3. **Support resume** — if interrupted, read `sprint-meta.yaml` to skip completed phases
4. **Carry revision findings** — on REVISE verdict, include prior findings in teammate spawn prompts

### State Directories
| Team | Working Dir | Persists? |
|------|-------------|-----------|
| Review Swarm | `.sprint/swarm/` | No — deleted after synthesis |
| Bug Swarm | `.bugswarm/` | Yes — until manually cleaned |
| Test Swarm | `.sprint/` (test files in `tests/`) | Tests persist, report in sprint |
| Health Check | `.health/` | Yes — persists across sprints for trends |
| Plan Swarm | `.sprint/.planning/` | No — cleaned with sprint |
| Arch Debate | `.sprint/` (ADR files) | Yes — ADRs are permanent records |

## Anti-Patterns

- **Broadcasting when a direct message suffices** — broadcasts are expensive (N messages for N teammates)
- **Teammates writing to the same file** — no file locking exists, last-write-wins
- **Lead doing teammate work** — if you spawned a team, let them work; don't duplicate effort
- **Skipping shutdown** — always send shutdown_request and TeamDelete, even on failure
- **Deep nesting** — teammates cannot create nested teams; use subagents (Task without team_name) for sub-work within a teammate
