# Observation: Prompt 00-C — Build File Catalog

**Scenario:** `00-project-init.md` → Prompt 00-C
**Date:** 2026-03-03

## Prompt Given

```text
Build a file catalog for this project so you can quickly navigate it later.
```

## Expected Behavior (from scenario)

1. Claude invokes `/catalog init` which triggers the catalog skill.
2. It scans the project structure and classifies files by role (model, route, service, test, config, docs).
3. Creates or updates `catalog.yaml`.
4. **Checkpoint:** `catalog.yaml` exists with entries for all scaffold files. Each file has a classification.

## Actual Behavior

### What Worked

- **Project explored** — Used an Explore agent (24 tool uses, ~1m 18s) to thoroughly scan the project structure.
- **Catalog content is accurate** — Correctly identified: app factory pattern, 9 source files across 5 packages, User model, health routes, placeholder services/utils, 2 test files, config files.
- **Project metadata captured** — Stack (Flask 3.0, SQLAlchemy, Celery+Redis, JWT, pytest), stage (v0.1.0), Python version (3.11).
- **Summary was helpful** — Clear breakdown of what exists and what's planned but not built.
- **Offered next step** — Asked what feature to tackle first.

### Issues / Gaps

1. **User did not invoke `/catalog` skill** — The prompt used natural language ("Build a file catalog") without explicitly calling `/heo-testing:catalog`. This is expected — skills should only run when explicitly invoked via slash command. The agent correctly treated it as a general request and answered with its own capabilities.
2. **Output format was freeform** — Without the skill, the agent produced `catalog.md` (Markdown in Claude's memory directory) rather than the structured `.claude/catalog/` output the skill produces. This is the expected difference between a general request and a skill invocation.
3. **Wrong output location** — Written to Claude's memory directory instead of the project. Understandable without the skill guiding output location.
4. **No role classification taxonomy** — "Purpose" column instead of formal categories. Again, expected without the skill's structure.
5. **MEMORY.md also written** — Agent wrote project MEMORY.md. Helpful side effect but not what the scenario was testing.
6. **Explore agent overhead** — 24 tool uses and 1m 18s for a small scaffold project.

### Severity Assessment

| Issue | Severity | Notes |
|-------|----------|-------|
| Skill not explicitly invoked by user | **Not a bug** | Skills should only trigger via explicit `/command` invocation |
| Wrong format (MD instead of YAML) | Low | Expected without skill — general request gets general output |
| Wrong location (memory dir instead of project dir) | Low | Expected without skill |
| No role classification taxonomy | Low | Expected without skill |
| Performance (1m 18s for small project) | Low | Explore agent is heavyweight for this task |

### Checkpoint Evaluation

- **`catalog.yaml` exists?** — NO. A `catalog.md` was created in the wrong location with the wrong format.
- **Entries for all scaffold files?** — YES (in the MD file, content coverage was good).
- **Each file has a classification?** — PARTIAL. Has "Purpose" descriptions but not formal role classifications.

## Recommendations

1. **Scenario spec needs updating** — The scenario should instruct the user to invoke `/catalog` explicitly rather than expecting natural language to trigger it. Skills are designed to be explicitly invoked.
2. The general-request output was still useful — the agent's freeform answer is fine for a non-skill interaction.
3. See `00-C-catalog-retry.md` for the explicit skill invocation result, which was excellent.
