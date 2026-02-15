# Ralph Wiggum: Catalog System Implementation

## Invocation Command

```bash
.dev/agentic-loops/resources/ralph-wiggum/scripts/setup-ralph-loop.sh "$(sed -n '/## TASK PROMPT/,/## GIT CREDENTIALS/{/## GIT CREDENTIALS/d;p}' RALPH_WIGGUM_PROMPT.md)" --completion-promise 'IMPLEMENTATION_COMPLETE' --max-iterations 3
```

## Task Overview

Implement the **Catalog Librarian** unified intelligence system (Phase 1) as specified in `docs/planning/IMPLEMENTATION_PLAN.md`.

This is a high-complexity task with clear success criteria, incremental milestones, and automated testing. Ralph will iteratively implement, test, validate, and commit.

---

## TASK PROMPT

### Mission

Build a **file classification and dependency tracking system** that serves as the foundation for unified code intelligence.

**Scope**: Phase 1 only (16 tasks, ~108k tokens budgeted)

### Implementation Requirements

Read and follow:
1. `docs/planning/IMPLEMENTATION_PLAN.md` - Architecture, phases, success criteria
2. `docs/planning/PLAN_REVIEW.md` - Critical specifications
3. `.dev/plans/catalog/catalog_build_prompt.md` - Detailed requirements

### Phase 1 Deliverables (16 Tasks)

Complete **all** of the following in order:

#### 1. Create unified `scripts/intelligence/` structure
- Create directory tree as specified in IMPLEMENTATION_PLAN
- Create `__init__.py`, `cli.py`, `config.py`, `build.py`, `cache.py`
- Create `components/`, `monitoring/`, `utils/`, `tests/` directories
- Add `__init__.py` to all package directories
- **Commit**: "feat: create scripts/intelligence directory structure"

#### 2. Implement BuildCache with SQLite (hash tracking)
- File: `scripts/intelligence/cache.py`
- SQLite schema: track artifacts, dependencies, file hashes (SHA-256)
- Methods: `mark_built(artifact, dependencies)`, `is_fresh(artifact, sources)`, `invalidate(artifact)`
- Use timestamp + hash for efficient change detection
- Tests: >80% coverage, test hash tracking, dependency invalidation, stale artifact detection
- **Commit**: "feat: implement BuildCache with hash tracking"

#### 3. Implement BuildGraph with DAG orchestration
- File: `scripts/intelligence/build.py` (partial)
- Topological sort for component ordering
- Methods: `add_component(name, deps)`, `build_order()`, `validate_dag()`
- Tests: DAG validation, cycle detection, correct topological order
- **Commit**: "feat: implement BuildGraph DAG orchestration"

#### 4. Implement system monitoring
- File: `scripts/intelligence/monitoring/system_monitor.py`
- Memory usage (warn at 75%, critical at 85%)
- Disk space (warn at 5GB free, critical at 1GB)
- CPU usage (info only)
- Methods: `get_system_health()`, `check_thresholds()`
- Format: `{"memory_percent": X, "disk_free_gb": Y, "cpu_percent": Z, "warnings": []}`
- Tests: threshold checking, warning generation
- **Commit**: "feat: implement system resource monitoring"

#### 5. Implement context window impact estimation
- File: `scripts/intelligence/monitoring/context_estimator.py`
- Estimate tokens for Haiku (100k), Sonnet (200k), Opus (200k)
- Calculate index size → token estimate
- Warn if >50% of budget
- Methods: `estimate_tokens(index_size, model)`, `recommend_model(index_size)`
- Output format in build report: `"📈 Context impact: 3200 tokens (3% of Haiku budget) ✅ SAFE"`
- Tests: token estimation accuracy, model recommendations
- **Commit**: "feat: implement context window impact estimation"

#### 6. Implement classifier component
- File: `scripts/intelligence/components/classifier.py`
- Load rules from `catalog.yaml` with defaults (if missing)
- Support 4 rule types: directory patterns, filename patterns, content regex, AST patterns (Python only)
- Multi-language support (Python, TypeScript/JS, Shell, Dart, SQL, Docker, Config)
- Assign primary category + confidence (high/medium/low)
- Methods: `classify_file(path)`, `classify_all(root_dir)`
- Acceptance tests: directory pattern matching, filename pattern matching, content regex, AST patterns
- Tests: >80% coverage, edge cases (no matches → uncategorized)
- **Commit**: "feat: implement file classifier component"

#### 7. Implement dependency_graph component
- File: `scripts/intelligence/components/dependency_graph.py`
- Extract imports via AST (import, from...import)
- Resolve to file paths (internal vs external)
- Build forward graph: "what does this import?"
- Build reverse graph: "what imports this?" (second pass)
- Handle circular imports without infinite loops
- Methods: `extract_imports(file)`, `build_graph(root_dir)`, `get_importers(file)`
- Acceptance tests: import extraction, path resolution, circular import handling
- Tests: >80% coverage, relative path resolution
- **Commit**: "feat: implement dependency graph component"

#### 8. Implement symbol_index component
- File: `scripts/intelligence/components/symbol_index.py`
- Pure Python AST parsing (no LSP)
- Extract: functions, classes, methods, modules
- Store: name, file, line number, docstring, scope
- Methods: `extract_symbols(file)`, `build_index(root_dir)`
- Output format: `[{"name": "X", "file": "Y", "line": Z, "type": "function", "docstring": "..."}]`
- Tests: >80% coverage, function/class/method extraction, nested scope handling
- **Commit**: "feat: implement symbol index component"

#### 9. Implement docstring_parser component
- File: `scripts/intelligence/components/docstring_parser.py`
- Parse Google-style docstrings from symbols
- Extract: summary, description, args, returns, raises, examples
- Store in symbol index
- Methods: `parse_docstring(docstring_text)`
- Output format: `{"summary": "...", "args": [...], "returns": {...}, "raises": [...], "examples": [...]}`
- Tests: >80% coverage, all docstring sections, malformed docstrings (graceful)
- **Commit**: "feat: implement docstring parser component"

#### 10. Implement utility modules
- File: `scripts/intelligence/utils/ast_utils.py` - AST helpers (walk, extract nodes)
- File: `scripts/intelligence/utils/file_utils.py` - File I/O (read, write, iterate)
- File: `scripts/intelligence/utils/hash_utils.py` - SHA-256 file hashing
- File: `scripts/intelligence/utils/json_utils.py` - JSON serialization with default handlers
- Methods and docstrings per Google style
- Tests: >80% coverage per module
- **Commit**: "feat: implement utility modules"

#### 11. Implement schema versioning
- File: `scripts/intelligence/schema.py`
- Add version field to all JSON outputs
- Implement migration functions for future schema changes
- Methods: `load_index(path)` (auto-migrate), `dump_index(data)` (current version)
- Tests: versioning, migration logic
- **Commit**: "feat: implement schema versioning and migrations"

#### 12. Create unified CLI entry point
- File: `scripts/intelligence/cli.py`
- Commands:
  - `build [--config PATH] [--incremental] [--force]` - Build all
  - `classify [--config PATH]` - Classification only
  - `deps [--config PATH]` - Dependencies only
  - `query --file PATH` - Single file info
  - `query --category NAME` - Files in category
  - `query --imports PATH` - Forward deps
  - `query --depends-on PATH` - Reverse deps
  - `query --summary` - Stats only
  - `status` - Health check
  - `watch [--config PATH] [--debounce 100]` - Watch mode
- Entry point: `python -m scripts.intelligence <command>`
- Help: `--help` for all commands
- Tests: command parsing, help output
- **Commit**: "feat: create unified CLI entry point"

#### 13. Wire build orchestrator
- File: `scripts/intelligence/build.py` (complete)
- Orchestrate DAG execution: classifier → dependency_graph → symbol_index → docstring_parser
- Cache invalidation: skip fresh components
- Execute components in order, collecting outputs
- Generate final `index.json` (unified output)
- Include system health + context report
- Sample report:
  ```
  📊 System Health: Memory 42%, Disk 127GB, CPU 15%
  🔨 Indexing complete: 1245 symbols in 3.2MB
  📈 Context impact: 3200 tokens (3% of Haiku budget) ✅ SAFE
  ```
- Tests: DAG execution order, cache skipping, output generation
- **Commit**: "feat: complete build orchestrator"

#### 14. Integration tests for Phase 1
- File: `scripts/intelligence/tests/test_integration.py`
- Create test fixtures (small codebase with known structure)
- Test end-to-end: build → classify → extract dependencies → index symbols
- Validate: output formats, completeness, accuracy
- Test acceptance criteria:
  - All acceptance tests from IMPLEMENTATION_PLAN pass
  - Exit codes correct (0 for success, 1 for config error, 2 for file error, 3 for partial)
  - Incremental builds work correctly
  - Build report generated and formatted
- Validation: Load output files, verify schema, sample data
- Tests: >80% coverage across all components
- **Commit**: "feat: add Phase 1 integration tests"

#### 15. Documentation for Phase 1
- File: `README.md` - Quick start, how to run, CLI reference
- File: `docs/ARCHITECTURE.md` - Component descriptions, data flow diagram
- Include examples: classification, querying, incremental builds
- Module docstrings: every module has purpose statement
- **Commit**: "docs: add Phase 1 documentation"

#### 16. Final Phase 1 validation and commit
- Run all tests: `pytest scripts/intelligence/tests/ -v`
- Verify coverage: >80%
- Test on real codebase: run full build on scripts/ directory
- Verify outputs: `index.json`, `file_classification.json`, `module_dependencies.json` exist and are valid JSON
- Test CLI: run `python -m scripts.intelligence build` successfully
- Verify exit codes (0, 1, 2, 3) with test scenarios
- Test incremental: modify one file, rebuild, verify only changed components reprocess
- Generate final report and verify format
- Create final commit summarizing Phase 1 completion
- **Commit message**: "feat: Phase 1 complete - unified catalog system working with all acceptance tests passing"

### Code Quality Requirements

- **Test-Driven Development**: Write tests first, then implementation
- **Google-style docstrings**: All functions, classes, modules
- **>80% coverage**: Unit tests for all components
- **Acceptance tests**: All tests from IMPLEMENTATION_PLAN must pass
- **Type hints**: For complex functions (Python 3.10+)
- **Error handling**: Graceful degradation per Design Constraints
- **Exit codes**: Implement 0, 1, 2, 3 correctly

### Success Criteria (Task Completion)

All of these must be true for `<IMPLEMENTATION_COMPLETE>`:

1. ✅ All 16 Phase 1 tasks completed
2. ✅ All unit tests passing (>80% coverage)
3. ✅ All acceptance tests passing (from IMPLEMENTATION_PLAN)
4. ✅ CLI commands working: `build`, `query --file`, `query --category`, `query --depends-on`, `status`
5. ✅ Incremental builds working: unchanged components skipped
6. ✅ Output files valid: `index.json`, `file_classification.json`, `module_dependencies.json`
7. ✅ Build report includes system health + context window impact
8. ✅ Exit codes correct: 0 (success), 1 (config), 2 (file), 3 (partial)
9. ✅ All changes committed locally with clear messages
10. ✅ Code reviewed: no obvious issues, follows Google style

### Iteration Strategy

**Iteration 1**: Tasks 1-6 (Structure, caching, DAG, monitoring, classifier)
- Commit every 500 lines locally
- By end: classifier working, basic monitoring

**Iteration 2**: Tasks 7-11 (Dependencies, symbols, docstrings, utils, schema)
- Commit every 500 lines locally
- By end: symbol indexing complete

**Iteration 3**: Tasks 12-16 (CLI, orchestrator, tests, docs, validation)
- Commit every 500 lines locally
- By end: Phase 1 complete, all tests passing

### Push to Remote

Push every 5000 lines of code changes to:
```
https://github.com/FrostyTeeth/claude_plugin_source
Branch: feat/implement-catalog
```

Use credentials from `.env.local`:
```
REPO_ORIGIN_URL=https://github.com/FrostyTeeth/claude_plugin_source.git
REPO_ORIGIN_PAT=<from .env.local>
```

Commands:
```bash
git remote add origin $REPO_ORIGIN_URL
git branch -M feat/implement-catalog
git push -u origin feat/implement-catalog
```

### When Complete

Signal completion by outputting:
```
<IMPLEMENTATION_COMPLETE>

Phase 1 Implementation Status:
- Tasks completed: 16/16
- Tests passing: ✅ (coverage >80%)
- Acceptance tests: ✅ All passing
- CLI working: ✅
- Incremental builds: ✅
- Documentation: ✅
- Code quality: ✅

Ready for Phase 2 (semantic layer).
```

---

## GIT CREDENTIALS

Git credentials should be stored in environment variables or `.env.local` (gitignored), never committed to version control.

```bash
# Set up credentials via environment
export REPO_ORIGIN_PAT="${REPO_ORIGIN_PAT:-}"  # Read from environment

# Use in git commands
git config --global credential.helper store
git push https://${REPO_ORIGIN_PAT}@github.com/FrostyTeeth/claude_plugin_source.git
```

---

## How Ralph Should Work

1. **Read requirements** - Understanding the 16 tasks, acceptance criteria, coding standards
2. **Implement iteratively** - Complete several tasks per iteration
3. **Commit frequently** - Every 500 lines locally: `git commit -m "feat/fix: clear message"`
4. **Test thoroughly** - Run tests after each component, validate acceptance criteria
5. **Push periodically** - Every 5000 lines: push to remote branch
6. **Document as you go** - Docstrings, type hints, test docstrings
7. **Iterate** - Get feedback on first iteration via exit attempt, improve next iteration
8. **Complete** - Signal `<IMPLEMENTATION_COMPLETE>` when all tasks done + all tests passing

---

## Reference Materials

- Implementation Plan: `docs/planning/IMPLEMENTATION_PLAN.md`
- Plan Review: `docs/planning/PLAN_REVIEW.md`
- Catalog Build Prompt: `.dev/plans/catalog/catalog_build_prompt.md`
- Standards: `standards/DOCSTRING_STYLE.md`, `standards/TEST_NAMING.md`

**Total budget**: ~108k tokens for Phase 1 (3 iterations × 36k tokens/iteration)

