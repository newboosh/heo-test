---
name: hybrid-payload
description: Reference for the 90/9/1 hybrid context payload format. Used by context-agent to structure context delivery into three tiers - RAW (inlined content), LINKED (fetchable references), and SUMMARY (narrative overview). Defines payload format, classification algorithm, and budget-constrained assembly.
model: opus
---

# Hybrid Payload Format

**You are assembling a context payload.** Use this format to deliver maximum context density to the primary agent while respecting token budget constraints.

## Overview

The hybrid payload delivers context in three tiers within a single markdown document:

| Tier | Budget | What It Contains | Token Cost |
|------|--------|-----------------|------------|
| **RAW** | 90% | Full file contents, code blocks, complete documents | Immediate (inlined) |
| **LINKED** | 9% | File paths + line ranges + one-line descriptions | Near-zero (fetched on demand) |
| **SUMMARY** | 1% | Narrative overview + payload map + key findings | Fixed overhead |

**Total budget target:** Under 100,000 tokens (see `token-budget` skill for details).

## Payload Structure

The payload is a single markdown document with six top-level sections:

```markdown
# Context Payload: [Task Description]

## META
## SUMMARY
## RAW
## LINKED
## Context Fingerprint
## ACK
```

### Section: META

Fixed overhead (~300 tokens). Provides budget accounting and staleness detection.

```markdown
## META
- **Task:** [task description]
- **Complexity:** simple | medium | complex
- **Budget:** [used] / [limit] tokens (RAW: [n] | LINKED: [n] | SUMMARY: [n])
- **Items:** RAW: [count] | LINKED: [count]
- **Generated:** [ISO 8601 timestamp]
- **Fingerprint:** [sha256]
- **Section Hashes:** RAW: [sha256] | LINKED: [sha256]
```

### Section: SUMMARY (Tier 3 — ~1%)

The primary agent reads this first to understand what context is available and why.

```markdown
## SUMMARY

[2-4 sentence narrative: what was gathered, why it matters, what to focus on first]

### Payload Map

| Tier | Section | ~Tokens | Why Included |
|------|---------|---------|--------------|
| RAW | primary-code | 12,000 | Files being modified |
| RAW | standards | 3,000 | Applicable conventions |
| RAW | test-patterns | 5,000 | TDD reference |
| LINKED | related-services | 0 (8,000 on fetch) | Integration context |
| LINKED | historical | 0 (3,000 on fetch) | ADR if stuck |

### Key Findings

- [Finding 1 — most important insight]
- [Finding 2]
- [Finding 3]
```

### Section: RAW (Tier 1 — ~90%)

Full content inlined. Each subsection has a metadata comment and a descriptive label.

```markdown
## RAW

### RAW:primary-code
<!-- source: explore-primary | relevance: 9 | tokens: ~12,000 -->
` ` `python
# file: app/services/payment_service.py (lines 1-245)
[full file contents]
` ` `

### RAW:standards
<!-- source: standards-lookup | relevance: 8 | tokens: ~3,000 -->
[full standards text]

### RAW:test-patterns
<!-- source: explore-tests | relevance: 7 | tokens: ~5,000 -->
` ` `python
# file: tests/services/test_order_service.py (lines 1-120)
[full file contents]
` ` `
```

**Conventions for RAW subsections:**
- Label format: `### RAW:<descriptive-label>`
- Metadata comment: `<!-- source: [agent/skill] | relevance: [0-10] | tokens: ~[count] -->`
- Code content: fenced block with language tag, file path header as `# file: path (lines N-M)`
- Prose content: inlined directly (standards, docs, plans)

### Section: LINKED (Tier 2 — ~9%)

File references the primary agent can fetch on demand. Near-zero token cost until fetched.

```markdown
## LINKED

### LINKED:related-services
<!-- source: explore-peripheral | relevance: 5 | fetch-cost: ~8,000 tokens -->
- `app/services/notification_service.py` lines 1-95 -- Sends payment notifications
- `app/services/order_service.py` lines 96-180 -- Downstream order fulfillment
- `app/api/payment_routes.py` lines 1-60 -- API endpoint definitions

### LINKED:schemas
<!-- source: process-map | relevance: 4 | fetch-cost: ~3,000 tokens -->
- `app/schemas/payment.py` lines 1-45 -- Request/response schemas
- `docs/openapi.yaml` lines 120-200 -- API spec for payments
```

**Conventions for LINKED subsections:**
- Label format: `### LINKED:<descriptive-label>`
- Metadata comment: `<!-- source: [agent/skill] | relevance: [0-10] | fetch-cost: ~[count] tokens -->`
- Each entry: `` `path` lines N-M -- one-line description ``
- No actual file content inlined

---

## Classification Algorithm

### Relevance Scoring (0-10)

Score each discovered item on these additive criteria:

| Points | Criterion | How to Determine |
|--------|-----------|------------------|
| +3 | File/symbol named in task description | String match against task text |
| +2 | File referenced in current plan step | Read current plan, check mentions |
| +3 | File will be directly modified by the task | Inferred from task + plan + code analysis |
| +2 | 1-hop dependency (imports or is imported by a modified file) | Dependency graph from librarian or explore |
| +1 | 2-hop dependency | Extended dependency walk |
| +2 | Same service/module directory as task target | Path prefix match |
| +1 | Same top-level domain directory | Top-level directory match |
| +1 | Modified in last 30 days | Git log or file mtime |
| +2 | Test file that maps to a modified file | `test_X.py` corresponds to `X.py` |

**Cap at 10.** Multiple criteria stack, but no item scores above 10.

### Tier Assignment

| Score | Tier | Action |
|-------|------|--------|
| 7-10 | RAW | Inline full content in payload |
| 4-6 | LINKED | Include path + line range + description |
| 1-3 | SUMMARY mention | Mentioned in narrative or omitted |

### Budget-Constrained Assembly

After scoring all items:

1. Sort all items by `relevance_score` descending
2. Walk the sorted list. For each item:
   - If score >= 7 and item fits in RAW budget → assign RAW
   - If score >= 7 but RAW budget exhausted → demote to LINKED
   - If score 4-6 and link entry fits in LINKED budget → assign LINKED
   - If LINKED budget exhausted → add to SUMMARY narrative
   - If score 1-3 → add to SUMMARY or omit
3. If total exceeds budget after first pass, demote lowest-scoring items from each tier

This ensures the most relevant content is always RAW, regardless of how much context was gathered.

---

## Complexity Scaling

The triage step (simple/medium/complex) affects how much of the budget is actually used:

| Complexity | Expected RAW | Expected LINKED | Typical Total |
|------------|-------------|----------------|---------------|
| Simple | 10-20K tokens | 2-5K | 15-25K |
| Medium | 30-60K tokens | 5-8K | 40-70K |
| Complex | 60-90K tokens | 7-9K | 70-100K |

Simple tasks will naturally produce smaller payloads because fewer sub-agents are spawned.

---

## Used By

- `agents/context-agent.md` — uses this format for all context delivery
- `.dev/agent-dev/Agent-Teams_Context_Agent.md` — Agent Teams variant
- `commands/context-payload.md` — triggers hybrid payload generation
- `skills/payload-consumer/` — consumer instructions reference this format

## Dependencies

- `skills/token-budget/` — budget allocation and estimation
- `skills/sub-agent-dispatch/` — sub-agent coordination feeds items for classification
- `skills/ack-protocol/` — ACK format used in the payload's ACK section
