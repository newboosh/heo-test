# Context Payload (Hybrid Context Delivery)

Explicitly invoke the Context Agent to produce a **hybrid context payload** — a tiered document with 90% raw content, 9% linked references, and 1% summary.

## Usage

```
/context-payload <task description>
```

## When to Use

Use `/context-payload` when you want the full tiered payload format. This is the recommended way to gather context before non-trivial tasks.

- Before implementing a new feature
- Before working in unfamiliar code areas
- When requirements change and prior context may be stale
- When you need both the code AND the navigation map

## What It Produces

A single markdown document with four sections:

| Section | Budget | Contains |
|---------|--------|---------|
| **META** | fixed | Task info, token budget, fingerprint, section hashes |
| **SUMMARY** | ~1% | Narrative overview, payload map table, key findings |
| **RAW** | ~90% | Full file contents, standards, test patterns (inlined) |
| **LINKED** | ~9% | File paths + line ranges for on-demand fetching |

**Total budget:** Up to 100K tokens. Simple tasks use less (~15-25K).

## How It Works

```
/context-payload "Add refund capability to payment service"
    |
    |-> Context Agent triages complexity (simple/medium/complex)
    |-> Batch 1: explore-primary + explore-tests + librarian + skills (parallel)
    |-> Batch 2: explore-peripheral + domain-specialist (if medium/complex)
    |-> Classify all items by relevance (0-10 scoring)
    |-> Assign tiers: score >= 7 -> RAW, 4-6 -> LINKED, 1-3 -> SUMMARY
    |-> Apply budget constraints (demote if tier full)
    |-> Deliver payload with ACK template
```

## After Receiving the Payload

1. Read SUMMARY first for orientation
2. Read RAW sections relevant to your current step
3. Note LINKED sections for later fetching if needed
4. Send PAYLOAD_ACK to confirm receipt (see `payload-consumer` skill)

## Examples

```
/context-payload Add refund capability to payment service
/context-payload Implement user notification preferences
/context-payload Refactor authentication to use JWT
/context-payload Create ERD for the order management system
```

## Related

- `/context` — Same context gathering, same hybrid payload format
- `skills/hybrid-payload/` — Payload format specification
- `skills/payload-consumer/` — How to process the payload
- `skills/token-budget/` — Budget allocation rules
- `skills/sub-agent-dispatch/` — Sub-agent coordination

Invokes the **context-agent**.
