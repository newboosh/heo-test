# Scenario 13: Advanced Features

## Features Exercised

- Commands: `/context-payload`
- Skills: hybrid-payload, payload-consumer, ack-protocol, composition-patterns,
  strategic-compact, token-budget, context-monitor, tool-design, agent-creator,
  skill-creator, hook-creator
- Agents: context-monitor
- Hooks: context-pressure (auto)

## Prerequisites

Multiple scenarios completed (enough history for context pressure to build).

## About This Scenario

These are advanced features that don't fit a single narrative thread. Each
prompt exercises a specific capability. They can be run independently.

## Prompts

### Prompt 13-A: Hybrid Context Payload

```text
I need to hand off the current project context to a new session. Package it
as a hybrid context payload using the 90/9/1 ratio.

Use /context-payload.
```

**What Should Happen:**
- Claude invokes `/context-payload` which uses the hybrid-payload skill.
- Creates a context package:
  - 90%: Structured context (file index, patterns, decisions)
  - 9%: Key code snippets (critical interfaces, models)
  - 1%: Natural language summary
- The payload-consumer skill describes how a receiving agent should
  unpack this payload.
- The ack-protocol skill structures the handoff confirmation.

**Checkpoint:** Context payload file created with 90/9/1 structure. It
captures the essential state of the project.

---

### Prompt 13-B: Strategic Compaction

```text
This session has been going on for a while and context is getting large.
Suggest what can be compacted or dropped to free up context space.
```

**What Should Happen:**
- The strategic-compact skill analyzes current context.
- Identifies: stale information, resolved issues, redundant context.
- Suggests what can be safely removed.
- The token-budget skill estimates token usage.
- The context-monitor agent (if running) has been tracking context pressure.

**Checkpoint:** Compaction suggestions with token savings estimates.

---

### Prompt 13-C: Context Pressure (Hook Test)

This hook fires automatically during long sessions. After many tool calls:

**What Should Happen:**
- The context-pressure hook tracks tool usage.
- When thresholds are reached, it suggests creating a checkpoint.
- Output appears as a system message: "Context pressure is building.
  Consider running /checkpoint."

**Checkpoint:** Context pressure warning appears after sustained tool usage.

---

### Prompt 13-D: Token Budget

```text
How many tokens have we used in this session? What's our budget?
```

**What Should Happen:**
- The token-budget skill estimates current token usage.
- Shows: tokens used, estimated remaining, budget status.

**Checkpoint:** Token usage estimate displayed.

---

### Prompt 13-E: Create a Custom Skill

```text
Create a new skill called "api-docs-generator" that generates OpenAPI
documentation from Flask routes. It should scan route files, extract
endpoint definitions, and produce a valid OpenAPI 3.0 YAML file.

Use /skill-creator.
```

**What Should Happen:**
- The skill-creator skill creates a new skill file.
- Generates the skill definition with: trigger conditions, instructions,
  expected inputs/outputs.
- Places the file in the skills/ directory.

**Checkpoint:** New skill file at skills/api-docs-generator/prompt.md (or
similar). Contains a valid skill definition.

---

### Prompt 13-F: Create a Custom Agent

```text
Create a new agent called "api-tester" that specializes in writing and
running API integration tests. It should know about our Flask patterns and
use the test client.

Use /agent-creator.
```

**What Should Happen:**
- The agent-creator skill creates a new agent definition.
- Generates the agent file with: role, capabilities, tools, instructions.
- Places it in the agents/ directory.

**Checkpoint:** New agent at agents/api-tester.md with a valid agent def.

---

### Prompt 13-G: Create a Custom Hook

```text
Create a hook that checks for hardcoded database URLs in Python files before
any tool use. It should warn if it finds a string matching a database
connection pattern outside of config files.

Use /hook-creator.
```

**What Should Happen:**
- The hook-creator skill creates a new hook.
- Generates the hook script with: event type (PreToolUse), matching logic,
  warning message.
- Places it in the hooks/ directory and registers it.

**Checkpoint:** New hook script created. Hook definition added to hooks.json.

---

### Prompt 13-H: Composition Patterns

```text
How should I compose multiple skills together for a complex workflow? For
example, combining context gathering, planning, and TDD into a single
automated flow?
```

**What Should Happen:**
- The composition-patterns skill explains how skills can be chained.
- Shows patterns for: sequential composition, parallel composition,
  conditional branching.
- References real examples from the plugin.

**Checkpoint:** Composition guide with patterns and examples.

---

### Prompt 13-I: Tool Design Reference

```text
I want to design a new tool for this plugin. What are the design standards?
```

**What Should Happen:**
- The tool-design skill provides the canonical tool design reference.
- Covers: naming, input/output contracts, error handling, testability.

**Checkpoint:** Tool design reference displayed.
