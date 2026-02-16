---
name: sub-agent-dispatch
description: Coordination patterns for context-agent sub-agents. Defines which sub-agents to spawn per complexity tier, prompt templates, the two-batch parallel execution pattern, and the result envelope format for collected items.
---

# Sub-Agent Dispatch

**You are the context agent dispatching sub-agents to gather context.** Use these patterns to coordinate parallel information gathering and collect structured results.

## Dispatch Table

| Sub-Agent | Type | When Spawned | What It Returns |
|-----------|------|-------------|-----------------|
| **explore-primary** | Explore | Always | Files directly involved in the task. Full contents for files < 300 lines; first 100 lines + total for larger files. |
| **explore-tests** | Explore | Always | Test files, fixtures, and factories for primary files. Representative test patterns. |
| **explore-peripheral** | Explore | Medium / Complex | Code that calls or is called by primary files. Dependency fan-out. |
| **librarian** | Librarian agent | Always | Catalog symbols, file locations, doc-to-code references for task scope. |
| **domain-specialist** | Explore | Complex only | Data flow trace: triggers, transformations, consumers, upstream/downstream. |

**In addition to sub-agents**, these skills run inline (not as separate agents):
- `plan-context` — current plan, meta-plan, roadmap
- `standards-lookup` — applicable coding standards
- `find-patterns` — similar implementations in codebase
- `gather-docs` — relevant documentation
- `prereq-check` — prerequisites and readiness

## Two-Batch Parallel Execution

Sub-agents and skills are dispatched in two batches. Batch 2 depends on Batch 1 results.

```
BATCH 1 (always, all in parallel)
 │
 ├─► Sub-agents via Task tool:
 │   ├─► explore-primary    "Find code directly related to {task}..."
 │   ├─► explore-tests      "Find test files for {task scope}..."
 │   └─► librarian          "CATALOG_REQUEST: {scope}"
 │
 ├─► Skills (inline, parallel):
 │   ├─► plan-context
 │   ├─► standards-lookup
 │   ├─► find-patterns
 │   ├─► gather-docs
 │   └─► prereq-check
 │
 └─► TaskList (inline)

 WAIT for all Batch 1 results
 ─────────────────────────────

BATCH 2 (conditional — medium/complex only, all in parallel)
 │
 ├─► explore-peripheral     Needs: primary file list from Batch 1
 ├─► domain-specialist      Needs: entity/model list from Batch 1
 └─► process-map skill      Needs: affected services from Batch 1

 WAIT for all Batch 2 results
 ─────────────────────────────

ASSEMBLY PHASE
 │
 ├─► Classify all items (relevance scoring)
 ├─► Apply budget constraints (tier assignment)
 ├─► Build payload document
 ├─► Compute fingerprint + section hashes
 └─► Deliver to primary agent
```

### Why Two Batches?

Batch 2 sub-agents need information from Batch 1 to be effective:
- `explore-peripheral` needs to know which files are primary (from explore-primary) to find their callers/callees
- `domain-specialist` needs to know which entities/models are involved (from explore-primary + librarian) to trace data flow
- `process-map` needs to know which services are affected (from explore-primary) to map process impact

Running them in Batch 1 without this info would produce unfocused, less relevant results.

## Prompt Templates

### explore-primary

```
Find all code directly related to: {task_description}

Focus on:
- Entry points (routes, CLI commands, event handlers)
- Core implementation files (services, models, utilities)
- Configuration files that affect this feature
- Schema definitions (request/response, database)

Include full file contents for files under 300 lines.
For larger files, include the first 100 lines and note the total line count.

Return each file as a discrete Item in this format:

#### Item: [descriptive-name]
- **File:** [path]
- **Lines:** [start]-[end]
- **Type:** code | config | schema
- **Relevance Hint:** critical | high | medium | low
- **Content:**
\`\`\`[language]
[file content]
\`\`\`
- **Why:** [1-sentence explanation of relevance]
```

### explore-tests

```
Find test files related to: {task_description}

Focus on:
- Unit tests for the primary files
- Integration tests that exercise this feature
- Test fixtures and factories used by these tests
- conftest.py files in relevant directories

Include full file contents for representative test files.
Prioritize tests that demonstrate patterns the primary agent should follow.

Return each file as a discrete Item in this format:

#### Item: [descriptive-name]
- **File:** [path]
- **Lines:** [start]-[end]
- **Type:** test
- **Relevance Hint:** critical | high | medium | low
- **Content:**
\`\`\`[language]
[file content]
\`\`\`
- **Why:** [1-sentence explanation of relevance]
```

### explore-peripheral (Batch 2)

```
Given these primary files: {primary_file_list}

Find code that depends on or is depended on by these files:
- Services that call functions in primary files
- Modules that import from primary files
- Files that primary files import from
- API routes that invoke primary services
- Event handlers triggered by primary code

Full contents only for files under 150 lines.
For larger files, include file path, line range, and a one-line description.

Return each as a discrete Item in this format:

#### Item: [descriptive-name]
- **File:** [path]
- **Lines:** [start]-[end]
- **Type:** code | config
- **Relevance Hint:** critical | high | medium | low
- **Content:**
\`\`\`[language]
[file content or "See file — too large to inline"]
\`\`\`
- **Why:** [1-sentence explanation of relevance]
```

### librarian

```
CATALOG_REQUEST: symbols and references related to {scope}

Provide:
- Relevant symbols from symbols.json (functions, classes, constants)
- File locations for each symbol
- Doc-to-code reference states (CURRENT, STALE, Broken)
- Any undocumented patterns relevant to the scope
```

### domain-specialist (Batch 2)

```
Given these entities/models: {entity_list}

Trace the data flow:
- What triggers create/modify these entities?
- What transformations occur?
- What downstream consumers read these entities?
- What external systems interact with this data?
- What business rules govern this flow?

Focus on the flow, not implementation details.

Return each discovery as a discrete Item in this format:

#### Item: [descriptive-name]
- **File:** [path]
- **Lines:** [start]-[end]
- **Type:** code | doc
- **Relevance Hint:** critical | high | medium | low
- **Content:**
\`\`\`[language]
[relevant code or description]
\`\`\`
- **Why:** [1-sentence explanation of relevance]
```

## Result Envelope Format

Every sub-agent returns results as a list of discrete **Items**. Each Item is independently classifiable by the context agent.

```markdown
## Sub-Agent Result: {agent-name}

### Metadata
- **Agent:** {explore-primary | explore-tests | explore-peripheral | librarian | domain-specialist}
- **Query:** {what was searched for}
- **Items Found:** {count}

### Items

#### Item: {descriptive-name}
- **File:** {absolute or relative path}
- **Lines:** {start}-{end}
- **Type:** code | doc | config | schema | test
- **Relevance Hint:** critical | high | medium | low
- **Content:**
` ` `{language}
{actual file content}
` ` `
- **Why:** {1-sentence explanation of relevance to the task}

#### Item: {next-item-name}
...
```

### Envelope Conventions

- **Relevance Hint** is advisory — the context agent applies its own scoring algorithm, but hints help prioritize when scores are tied
- **Content** field is optional for LINKED-tier candidates — the sub-agent can return just path + lines + description
- **Type** helps the token estimator choose the right formula (code vs prose vs config)
- Sub-agents should aim for 5-15 items per result. More than 20 items suggests the scope was too broad.

## Complexity-Based Dispatch

| Complexity | Batch 1 Sub-Agents | Batch 2 Sub-Agents | Skills (all run in Batch 1) |
|------------|--------------------|--------------------|--------|
| Simple | explore-primary, explore-tests, librarian | (none) | plan-context, standards-lookup, find-patterns, gather-docs, prereq-check |
| Medium | explore-primary, explore-tests, librarian | explore-peripheral | plan-context, standards-lookup, find-patterns, gather-docs, prereq-check |
| Complex | explore-primary, explore-tests, librarian | explore-peripheral, domain-specialist | plan-context, standards-lookup, find-patterns, gather-docs, prereq-check, process-map |

**Note:** All five core skills run in Batch 1 regardless of complexity. Only `process-map` is conditional (complex only). In Agent Teams mode, the librarian is contacted via team mailbox instead of the Task tool.

## Used By

- `agents/context-agent.md` — follows this dispatch pattern during context gathering
- `.dev/agent-dev/Agent-Teams_Context_Agent.md` — Agent Teams variant

## Dependencies

- `skills/hybrid-payload/` — envelope items feed into the classification algorithm
- `skills/token-budget/` — item content sizes are measured during assembly
