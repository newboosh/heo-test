---
name: payload-consumer
description: Instructions for agents receiving a hybrid context payload. Explains reading order, how to fetch LINKED content on demand, context window management, and the ACK protocol for confirming payload receipt.
model: haiku
---

# Consuming a Context Payload

**You have received a hybrid context payload.** Follow these steps to process it efficiently and confirm receipt.

## Reading Order

1. **Read META** — note the task description, complexity, and budget usage
2. **Read SUMMARY** — understand what was gathered, scan the Payload Map table, note Key Findings
3. **Scan RAW section headers** — identify which `### RAW:` subsections are relevant to your immediate task step. Read those sections in full.
4. **Note LINKED sections** — these are available but not yet loaded. Record the file paths for later.
5. **Confirm receipt** — send the ACK (see below)

## ACK Protocol

After reading the payload, confirm receipt so the context agent (or lead) knows the payload arrived intact. See `skills/ack-protocol/SKILL.md` for the full protocol spec, including re-delivery workflow.

**Quick reference:**

```markdown
PAYLOAD_ACK:
  fingerprint: {echo the Fingerprint from META}
  raw_sections: {count of ### RAW: subsections you received}
  linked_sections: {count of ### LINKED: subsections you received}
  status: complete | partial
  missing: []
```

Send `complete` when all sections received and counts match META. Send `partial` if sections are truncated or missing — the sender will re-deliver only the missing content.

## Fetching LINKED Content

LINKED entries cost zero tokens until you fetch them. To retrieve:

```
Read tool:
  file_path: {path from LINKED entry}
  offset: {start line}
  limit: {end line - start line}
```

**When to fetch:**
- Your current task step references a file listed in LINKED
- You need to understand an interface or dependency not fully captured in RAW
- You're debugging and need broader context

**When NOT to fetch:**
- You're just starting — focus on RAW first
- The LINKED description is sufficient for your needs
- Budget is tight and you want to preserve context window space

## Context Window Management

The payload is designed to be large (up to 100K tokens). Manage your context window:

### Prioritize by Relevance

RAW sections are ordered by relevance score (highest first). If you need to skim, focus on the first few RAW sections — they're the most critical.

### Deprioritize After Extraction

After you've read a RAW section and extracted what you need (e.g., understood the data model, noted the API pattern), you can mentally deprioritize it. You don't need to re-read it on every reasoning step.

### Fetch LINKED Selectively

Each LINKED fetch adds to your context. Only fetch what your current step requires. The one-line descriptions in LINKED are designed to help you decide without fetching.

### Budget Awareness

The META section shows total token usage. If the payload used 85K of 100K tokens, you have ~15K tokens of headroom for your own reasoning, tool calls, and LINKED fetches. Plan accordingly.

## Handling Partial Payloads

If your ACK status is `partial`:

1. Check which sections are missing (likely LINKED, which appears last)
2. The RAW sections you did receive are still valid — proceed with those
3. Report the partial status so the context agent can re-deliver missing sections
4. If LINKED sections are missing, you can still use Glob/Grep to find files manually

## Example Workflow

```
1. Receive payload (100K tokens)
2. Read SUMMARY (30 seconds)
   → "This payload covers the payment service refactor.
      Key files are in RAW:primary-code and RAW:data-structures.
      Related notification code is in LINKED:related-services."
3. Read RAW:primary-code (payment_service.py — the main file I'm modifying)
4. Read RAW:standards (coding conventions I need to follow)
5. Read RAW:test-patterns (how existing tests are structured)
6. Send ACK: complete, 5 RAW sections, 3 LINKED sections
7. Start implementation...
8. Later: need to understand notification integration
   → Fetch LINKED:related-services → Read notification_service.py lines 1-95
9. Continue implementation with full context
```

## Used By

Any agent that receives context from the context agent. Add this skill to agent definitions that participate in the context workflow:

```yaml
skills:
  - payload-consumer
```

## Dependencies

- `skills/hybrid-payload/` — defines the format this skill consumes
- `skills/ack-protocol/` — full ACK protocol spec (referenced in ACK Protocol section above)
