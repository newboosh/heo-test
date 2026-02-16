# Context Payload: {TASK_DESCRIPTION}

## META
- **Task:** {TASK_DESCRIPTION}
- **Complexity:** {simple | medium | complex}
- **Budget:** {TOTAL_USED} / {TOTAL_LIMIT} tokens (RAW: {RAW_USED} | LINKED: {LINKED_USED} | SUMMARY: {SUMMARY_USED})
- **Items:** RAW: {RAW_COUNT} | LINKED: {LINKED_COUNT}
- **Generated:** {ISO_8601_TIMESTAMP}
- **Fingerprint:** {SHA256_OF_PAYLOAD}
- **Section Hashes:** RAW: {RAW_HASH} | LINKED: {LINKED_HASH}

---

## SUMMARY

{2-4 sentence narrative: what was gathered, why it matters, what the primary agent should focus on first.}

### Payload Map

| Tier | Section | ~Tokens | Why Included |
|------|---------|---------|--------------|
| RAW | {label} | {count} | {reason} |
| LINKED | {label} | 0 ({fetch_cost} on fetch) | {reason} |

### Key Findings

- {Finding 1 — most important insight}
- {Finding 2}
- {Finding 3}

---

## RAW

### RAW:{label}
<!-- source: {agent_or_skill} | relevance: {0-10} | tokens: ~{count} -->
```{language}
# file: {path} (lines {start}-{end})
{file contents}
```

### RAW:{label}
<!-- source: {agent_or_skill} | relevance: {0-10} | tokens: ~{count} -->
{prose content — standards, docs, plans}

---

## LINKED

### LINKED:{label}
<!-- source: {agent_or_skill} | relevance: {0-10} | fetch-cost: ~{count} tokens -->
- `{path}` lines {start}-{end} -- {one-line description}
- `{path}` lines {start}-{end} -- {one-line description}

---

## Context Fingerprint
- **Sources:**
  - `{path}` — {hash}
  - `{path}` — {hash}

---

## ACK (for primary agent to complete)

```
PAYLOAD_ACK:
  fingerprint: {echo the Fingerprint hash from META}
  raw_sections: {count of RAW subsections received}
  linked_sections: {count of LINKED subsections received}
  status: complete | partial
  missing: [{list sections not received, if partial}]
```
