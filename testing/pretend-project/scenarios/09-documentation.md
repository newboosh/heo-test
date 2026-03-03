# Scenario 09: Documentation and Librarian Deep Test

## Features Exercised

- Commands: `/update-docs`, `/update-codemaps`
- Skills: librarian, gather-docs
- Agents: librarian, doc-updater

All six librarian subcommands are exercised: audit, find, place, stale,
coverage, orphans.

## Prerequisites

Scenarios 04-06 completed (auth module built). Ideally also some of the
team swarm work from 08 so multiple modules exist. See PROJECT_GROWTH.md
stages 1-5 for what should be in place.

## Prompts

### Prompt 09-A: Initial Documentation Audit

```text
Run a complete documentation audit. I want to know: what's documented,
what's missing, what's stale, and what's orphaned.

Start with /librarian audit.
```

**What Should Happen:**
- Claude invokes the librarian agent with an audit command.
- The agent inventories every file in docs/:
  - architecture.md — exists but says "planned" for implemented features
  - api/ — may have auth.md if scenario 04 created it
  - No guides/, no ops/, no contributing.md, no changelog
- Reports:
  - Documented: architecture overview, health endpoint (implicit)
  - Stale: architecture.md references "planned" modules that now exist
  - Missing: API docs for implemented endpoints, deployment guide,
    contributing guide, testing guide, changelog
  - Orphaned: (none yet, but will appear later)

**Checkpoint:** Audit report lists at least 8 missing documentation items
and flags architecture.md as stale.

---

### Prompt 09-B: Documentation Coverage Report

```text
What percentage of the codebase has corresponding documentation? Show me a
coverage report broken down by module.

/librarian coverage
```

**What Should Happen:**
- Librarian calculates documentation coverage:
  - auth module: routes/auth.py, services/auth_service.py → docs/api/auth.md
    exists? Partial coverage.
  - task module: routes/tasks.py → docs/api/tasks.md exists? No coverage.
  - health: routes/health.py → no dedicated doc. Low coverage.
  - models: user.py, task.py → no model documentation. Zero coverage.
  - utils: validators.py, decorators.py → no utility docs.
- Produces a coverage percentage per module and overall.

**Checkpoint:** Coverage report shows <30% documentation coverage. Each
module listed with its coverage status. Clear gap identification.

---

### Prompt 09-C: Find Stale Documentation

```text
Which documentation files are stale — they describe something that has
changed since the doc was written?

/librarian stale
```

**What Should Happen:**
- Librarian compares doc content against actual code:
  - architecture.md says "Modules (planned)" but auth and tasks are now
    implemented → STALE
  - architecture.md may reference old file paths or missing modules
  - Any API docs that describe endpoints with outdated request/response
    formats → STALE
- Reports each stale doc with what specifically is outdated.

**Checkpoint:** At least architecture.md flagged as stale with specific
lines that are outdated. Each stale finding includes the source-of-truth
file that contradicts it.

---

### Prompt 09-D: Find Orphaned Documentation

```text
Are there any docs that reference code or features that no longer exist?

/librarian orphans
```

**What Should Happen:**
- Librarian scans docs for references to code that doesn't exist:
  - If any doc references a function/class/file that was removed or renamed
  - If an ADR references an approach that was abandoned
  - Cross-references import paths, function names, file paths in docs
    against actual codebase
- At this stage, orphans are unlikely (project is young), but the mechanism
  should be exercised.

**Checkpoint:** Orphan scan completes. Either "no orphans found" or specific
findings. The mechanism ran and produced a report.

---

### Prompt 09-E: Find Documentation by Topic

```text
Find all documentation related to authentication — including inline code
comments, docstrings, and dedicated doc files.

/librarian find "authentication"
```

**What Should Happen:**
- Librarian searches across:
  - doc files (architecture.md, api/auth.md if it exists)
  - code comments and docstrings in auth-related files
  - ADRs that discuss auth (001-jwt-auth.md)
  - Test files that document auth behavior
  - README if it mentions auth setup
- Returns a ranked list of relevant files with excerpts.

**Checkpoint:** Search results include auth route, auth service, auth tests,
and any auth documentation. Results are ranked by relevance.

---

### Prompt 09-F: Find Documentation by Topic (Second Query)

```text
/librarian find "database migrations"
```

**What Should Happen:**
- Searches for migration-related docs and code.
- Finds: migrations/README, any references in ops docs, model files with
  schema definitions.
- May flag that migration documentation is thin/missing.

**Checkpoint:** Results show what exists and implicitly what's missing.

---

### Prompt 09-G: Place New Documentation

```text
I want to write documentation for the task management API. Where should it
go? What sections should it have? What format should it follow?

/librarian place "task API documentation"
```

**What Should Happen:**
- Librarian analyzes existing doc structure and conventions.
- Recommends: docs/api/tasks.md (following the pattern of api/auth.md if
  it exists, or suggesting the api/ directory structure).
- Suggests sections: endpoint list, request/response examples, error codes,
  authentication requirements, pagination.
- References the project's doc conventions (if any established).

**Checkpoint:** Placement recommendation with a suggested file path,
directory structure, and content outline. Follows existing conventions.

---

### Prompt 09-H: Place New Documentation (Architecture Decision)

```text
We made a decision about how to handle real-time notifications. Where should
the ADR go?

/librarian place "notification transport ADR"
```

**What Should Happen:**
- Recognizes the ADR pattern (docs/adr/NNN-title.md).
- Suggests next sequential number (e.g., docs/adr/005-notification-transport.md).
- Provides ADR template: context, decision, consequences, status.

**Checkpoint:** Correct ADR path suggested with template structure.

---

### Prompt 09-I: Gather Documentation for a Task

```text
I'm about to implement the comments feature. Gather all documentation I'll
need — existing patterns, data model conventions, API conventions, test
patterns, and any relevant ADRs.

Use /gather-docs "comments feature implementation".
```

**What Should Happen:**
- Gathers from multiple sources:
  - Model patterns: user.py, task.py (field naming, relationships, mixins)
  - Route patterns: auth.py, tasks.py (blueprint structure, error handling)
  - Service patterns: auth_service.py, task_service.py (business logic layer)
  - Schema patterns: task_schema.py (marshmallow serialization)
  - Test patterns: test_auth.py, test_tasks.py (naming, fixtures, structure)
  - Standards: project-standards.yaml, TEST_NAMING.md conventions
  - Architecture: docs/architecture.md (where comments fits)
  - Relevant ADRs: soft-delete (002), threaded-comments (004 if exists)
- Organizes into a reference package with code snippets.

**Checkpoint:** Comprehensive reference package. A developer reading it would
know exactly how to implement comments following all existing conventions.

---

### Prompt 09-J: Gather Docs (Cross-Module)

```text
/gather-docs "adding rate limiting to all API endpoints"
```

**What Should Happen:**
- Recognizes this is a cross-cutting concern.
- Gathers: existing rate_limiter.py (if built in auth stage), middleware
  patterns, route decorator patterns, config patterns.
- References any performance-related ADRs.
- Notes which endpoints already have rate limiting and which don't.

**Checkpoint:** Cross-module reference showing every endpoint and its
current rate limiting status, plus the pattern to apply.

---

### Prompt 09-K: Update Docs After Feature Completion

```text
The authentication module is fully implemented and tested. Update all
documentation to reflect what was actually built. Make sure architecture.md
no longer says "planned" for auth, and create API docs if they don't exist.

Use /update-docs.
```

**What Should Happen:**
- Claude invokes `/update-docs` which spawns the doc-updater agent.
- The agent:
  1. Reads all auth source code (routes, services, models, schemas)
  2. Reads existing docs (architecture.md)
  3. Updates architecture.md: "Authentication" section reflects reality
  4. Creates docs/api/auth.md if it doesn't exist:
     - POST /api/auth/register — request body, response, errors
     - POST /api/auth/login — request body, JWT response, errors
  5. Updates README if needed (auth setup instructions)
  6. Generates from source of truth — every doc statement traceable to code
- All docs generated from code, not invented.

**Checkpoint:** architecture.md updated. API docs created/updated. Every
documented endpoint matches the actual implementation. No "planned" language
for implemented features.

---

### Prompt 09-L: Update Docs (Multiple Modules)

```text
We've now implemented auth, tasks, and workspaces. Do a full documentation
update for all three modules. Create any missing API docs, update
architecture.md, and make sure everything is in sync.

/update-docs
```

**What Should Happen:**
- Doc-updater processes all three modules.
- Creates or updates: api/auth.md, api/tasks.md, api/workspaces.md.
- Updates architecture.md to reflect three implemented modules.
- Cross-references (e.g., task docs mention auth requirements).

**Checkpoint:** Three API doc files exist. Architecture doc reflects reality
for all three modules.

---

### Prompt 09-M: Update Code Maps

```text
Generate module dependency maps and data model diagrams for the current
state of the project.

/update-codemaps
```

**What Should Happen:**
- Analyzes import graphs across all modules.
- Produces:
  - Module dependency map: which modules import from which
  - Data model diagram: entities and their relationships
  - Request flow: how a request moves through routes → services → models
- Updates docs/diagrams/ with current maps.

**Checkpoint:** Diagram files created/updated in docs/diagrams/. Dependency
map shows: routes depend on services, services depend on models, middleware
is cross-cutting.

---

### Prompt 09-N: Update Code Maps (After Refactor)

```text
I moved some code around during refactoring. Update the code maps to reflect
the current structure.

/update-codemaps
```

**What Should Happen:**
- Re-scans the codebase and regenerates maps.
- Diffs against previous maps and reports what changed.

**Checkpoint:** Maps reflect refactored structure. Diff shows what moved.

---

### Prompt 09-O: Full Audit After Documentation Buildout

```text
We've been adding documentation throughout the sprint. Run another full
audit to see how coverage has improved and what gaps remain.

/librarian audit
```

**What Should Happen:**
- Second audit shows improved coverage:
  - API docs exist for implemented modules
  - architecture.md is no longer stale
  - ADRs exist for key decisions
- Remaining gaps: ops docs, contributing guide, changelog, diagrams.

**Checkpoint:** Coverage improved from <30% to 60%+. Remaining gaps are
clearly identified for the next sprint.

---

### Prompt 09-P: Librarian Coverage After Buildout

```text
/librarian coverage
```

**What Should Happen:**
- Shows per-module coverage improvement.
- Highlights which modules now have full coverage and which still need work.

**Checkpoint:** Comparative report showing before/after coverage.
