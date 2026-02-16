---
name: token-budget
description: Token estimation and budget management for hybrid context payloads. Provides estimation formulas, budget allocation rules, overflow handling, and running tally logic. Used by context-agent during payload assembly.
---

# Token Budget

**You are tracking token usage during payload assembly.** Use these formulas and rules to stay within budget while maximizing context density.

## Estimation Formulas

Token counts are approximate. Different content types have different token densities:

| Content Type | Formula | Rationale |
|-------------|---------|-----------|
| Code (Python, JS, etc.) | `len(text) / 3.5` | Shorter tokens: operators, brackets, keywords |
| Prose (English) | `len(text) / 4.0` | Standard English tokenization |
| YAML / Config | `len(text) / 3.8` | Between code and prose |
| Markdown (mixed) | `len(text) / 3.75` | Default for mixed content |

**`len(text)`** = character count of the content string.

These are estimates. Build in headroom (see below) to absorb estimation error.

## Budget Allocation

Default allocation for a 100K token payload:

| Tier | Budget | Tokens | Purpose |
|------|--------|--------|---------|
| META | fixed | ~300 | Overhead: task info, budget, fingerprint, section hashes |
| SUMMARY | 1% | ~800 | Narrative + payload map + key findings |
| LINKED | 9% | ~9,000 | File references with descriptions |
| RAW | 90% | ~90,000 | Full inlined content |
| **Total** | **100%** | **~100,000** | |

## Headroom Rule

**Target 90% of each tier's budget as the effective limit.**

| Tier | Nominal Budget | Effective Limit | Headroom |
|------|---------------|-----------------|----------|
| RAW | 90,000 | 81,000 | 9,000 |
| LINKED | 9,000 | 8,100 | 900 |
| SUMMARY | 800 | 720 | 80 |

This 10% headroom absorbs token estimation errors. If an item's estimated tokens are 5,000 but actual tokens are 5,500, the headroom prevents a budget overrun.

## Running Tally

The context agent maintains a running tally during assembly. After each item is assigned to a tier:

```
Budget State:
  raw_limit:     81,000  (effective, with headroom)
  raw_used:      [running total]
  raw_remaining: [limit - used]

  linked_limit:  8,100
  linked_used:   [running total]
  linked_remaining: [limit - used]

  summary_limit: 720
  summary_used:  [running total]
  summary_remaining: [limit - used]

  total_used:    [sum of all tiers + META overhead]
  total_remaining: [100,000 - total_used]
```

Update the tally after each item is placed. Check `remaining >= 0` before placing the next item.

## Overflow Handling

When a tier's budget is exhausted, demote the item to the next tier down:

```
RAW budget full?
  → Demote lowest-scoring RAW item to LINKED
  → Re-check: does the new item fit in RAW now?
    → Yes: assign RAW
    → No: assign new item to LINKED

LINKED budget full?
  → Add to SUMMARY narrative only (mention the reference exists)

SUMMARY budget full?
  → Omit (item is not included in payload)
```

**Demotion always targets the lowest-scoring item in the tier**, not the current item. This ensures the highest-relevance content always stays in the highest tier.

## Complexity-Based Scaling

Not every payload uses the full 100K budget. The triage step determines expected usage:

| Complexity | Expected Total | Sub-Agents Spawned |
|------------|---------------|-------------------|
| Simple | 15-25K tokens | explore-primary, explore-tests, librarian |
| Medium | 40-70K tokens | + explore-peripheral |
| Complex | 70-100K tokens | + domain-specialist |

For simple tasks, most of the budget goes unused. This is correct — don't pad a simple payload to fill the budget.

## Estimation Accuracy Notes

- Token estimates can vary 10-20% from actual tokenizer output
- Code with many short identifiers (Go, Rust) trends toward `/ 3.0`
- Prose with long words (medical, legal) trends toward `/ 4.5`
- The headroom rule compensates for these variations
- When in doubt, round estimates up (overestimate tokens = conservative budget use)

## Used By

- `agents/context-agent.md` — tracks budget during payload assembly
- `skills/hybrid-payload/` — references this skill for budget rules

## Dependencies

None. This skill is standalone.
