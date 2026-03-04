# Observation: Prompt 00-C (Retry) — Build File Catalog with Explicit Skill

**Scenario:** `00-project-init.md` → Prompt 00-C (retry with explicit `/heo-testing:catalog`)
**Date:** 2026-03-03

## Prompt Given

```text
Build a file catalog for this project so you can quickly navigate it later. use /heo-testing:catalog
```

## Expected Behavior (from scenario)

1. Claude invokes `/catalog init` which triggers the catalog skill.
2. It scans the project structure and classifies files by role (model, route, service, test, config, docs).
3. Creates or updates `catalog.yaml`.
4. **Checkpoint:** `catalog.yaml` exists with entries for all scaffold files. Each file has a classification.

## Actual Behavior

### What Worked

- **Skill properly invoked** — `/heo-testing:catalog` loaded successfully.
- **Thorough project scan** — Read all 16 files, checked for multiple file types (.py, .yaml, .yml, .toml, .cfg, .ini, .json, .html, .css, .js).
- **Correct output location** — Files created in `.claude/catalog/` inside the project directory (not Claude's memory directory).
- **Structured output** — Created three artifacts:
  1. `.claude/catalog/config.yaml` (74 lines) — Classification rules with categories, pattern matching, priority ordering
  2. `.claude/catalog/indexes/file_classification.json` (163 lines) — Every file classified with confidence levels, matched rules, and summaries
  3. `.claude/catalog/indexes/module_dependencies.json` (94 lines) — Import graph with stdlib/third_party/local type annotations
- **Role taxonomy** — Files classified into proper categories: app_factory, config, model, route, service, util, test, migration, docs, build, package_init.
- **Confidence scoring** — Each classification has a confidence level (high/medium).
- **Dependency graph** — Caught that `config.py` is orphaned (defined but not imported by `app.py`). Good insight.
- **Summary table** — Clean category-by-category summary with file counts and key contents.
- **pyproject.toml dual-classified** — Appears in both "config" (medium confidence) and "build" (high confidence), handled by priority ordering.

### Issues / Gaps

1. **Format differs from scenario expectation** — Scenario expected `catalog.yaml` (single YAML file). Skill produced a richer structure: `config.yaml` + two JSON index files. This is arguably *better* than the scenario spec, but deviates from it.
2. **No `catalog.yaml` at project root** — The scenario checkpoint expects `catalog.yaml` at the project root. The actual output is in `.claude/catalog/`. Either the scenario needs updating or the skill needs a root-level summary file.
3. **Explicit invocation is the intended design** — Skills are meant to be triggered via explicit `/command` invocation, not natural language. The first attempt (without the skill) is the expected behavior for a general request.
4. **`config.yaml` rules are aspirational** — The `ast_content` rule type (e.g., `class_inherits:db.Model`, `decorator:app.route`) appears to be a schema the agent invented, not something the catalog skill actually executes. The classification was done manually by the agent reading files, not by running these rules programmatically.
5. **Empty categories included** — service and util categories have 0 files but are still listed. Minor — could be useful as placeholders or could be noise.

### Severity Assessment

| Issue | Severity | Notes |
|-------|----------|-------|
| Explicit invocation required | **By design** | Skills are intentionally triggered via slash commands only |
| Output format differs from scenario spec | Low | The actual format is richer/better, scenario spec may need updating |
| No `catalog.yaml` at project root | Low | `.claude/catalog/` location is reasonable, scenario may need updating |
| `ast_content` rules are fictional | Low | Config is aspirational — no harm, but slightly misleading |

### Checkpoint Evaluation

- **`catalog.yaml` exists with entries for all scaffold files?** — PARTIAL. No `catalog.yaml` at root, but `.claude/catalog/indexes/file_classification.json` covers all 16 files comprehensively.
- **Each file has a classification?** — YES. All files classified into categories with confidence levels.

### Comparison: First Attempt vs Retry

| Aspect | First attempt (no skill) | Retry (with skill) |
|--------|-------------------------|---------------------|
| Skill invoked | No | Yes |
| Output location | Claude memory dir | Project `.claude/catalog/` |
| Output format | Markdown table | YAML config + JSON indexes |
| Classification taxonomy | Freeform "Purpose" | Formal categories with rules |
| Dependency tracking | None | Full import graph with types |
| Confidence scoring | None | High/Medium per file |
| Quality | Good content, wrong format/location | Excellent across the board |

## Recommendations

1. **Scenario spec should be updated** — The `.claude/catalog/` structure with config + indexes is richer than a single `catalog.yaml`. Update the scenario to expect this format.
2. **Scenario prompts should use explicit `/catalog` invocation** — Since skills are designed to be triggered via slash commands, the scenario prompt should include the explicit command.
3. The dependency graph catching the orphaned `config.py` is a genuine value-add — consider highlighting this in catalog skill docs.
