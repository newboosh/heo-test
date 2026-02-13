---
name: ack-protocol
description: Reusable acknowledgment protocol for confirming delivery of structured payloads between agents. Defines the ACK format, status values, and re-delivery workflow. Used by context payloads and any inter-agent delivery that needs confirmation.
---

# ACK Protocol

**You are confirming receipt of a structured payload.** Use this protocol to acknowledge delivery and flag any missing content.

## ACK Format

```markdown
PAYLOAD_ACK:
  fingerprint: {echo the Fingerprint hash from the payload's META section}
  raw_sections: {count of RAW subsections received}
  linked_sections: {count of LINKED subsections received}
  status: complete | partial
  missing: [{list of missing section labels, if partial}]
```

## Status Values

| Status | Meaning | Sender Action |
|--------|---------|---------------|
| `complete` | All sections received, item counts match META | None — proceed with work |
| `partial` | Some sections truncated or missing | Re-send missing sections or convert to different format |

## When to Send

Send an ACK immediately after reading a payload's META and scanning section headers. Don't wait until you've read all content — the ACK confirms *structural receipt*, not comprehension.

## Why ACK Matters

- Context windows can silently truncate long payloads
- Sections at the end (typically LINKED) are most vulnerable to truncation
- Without ACK, the sender has no way to detect lost content
- A `partial` ACK triggers re-delivery of just the missing sections

## Re-Delivery on Partial ACK

When the sender receives `status: partial`:

1. Check the `missing` list for specific section labels
2. Re-send only the missing sections (not the full payload)
3. If re-delivery would exceed the receiver's remaining context budget, convert missing RAW sections to LINKED format (path + line range only)
4. The receiver sends a second ACK for the re-delivered content

## Verification

The receiver verifies structural completeness by comparing:
- `raw_sections` count against the META `Items: RAW: {count}` value
- `linked_sections` count against the META `Items: LINKED: {count}` value
- `fingerprint` echoed back to confirm identity (not integrity — the hash is from the sender's META, not recomputed)

## Used By

- `skills/payload-consumer/` — receiving agents use this to confirm context payload receipt
- `skills/hybrid-payload/` — payload template includes the ACK section
- `agents/context-agent.md` — processes ACK responses
- `.dev/agent-dev/Agent-Teams_Context_Agent.md` — processes PAYLOAD_ACK via mailbox

## Dependencies

None. This protocol is standalone and reusable.
