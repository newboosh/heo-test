# Scenario 09b: Catalog Deep Test

## Features Exercised

- Commands: `/catalog init`, `/catalog build`, `/catalog query`,
  `/catalog status`
- Skills: catalog

## Prerequisites

Scenario 00 completed (initial catalog built from scaffold). Best results
when run after scenarios 04-08 so the project has grown to 40+ files across
multiple modules (see PROJECT_GROWTH.md stages 1-5).

## About This Scenario

The catalog system classifies every file in the project by role, purpose,
and relationships. This scenario exercises all four subcommands extensively,
testing classification accuracy, query flexibility, incremental updates,
and health reporting.

## Prompts

### Prompt 09b-A: Init on Bare Scaffold

(Run this at Stage 0 if not already done in Scenario 00.)

```text
Build a file catalog from scratch. Classify every file in the project by
its role: model, route, service, test, config, docs, migration, utility.

/catalog init
```

**What Should Happen:**
- Scans the project tree.
- Classifies ~15 scaffold files:
  - model: models/user.py
  - route: routes/health.py
  - service: (empty, just __init__.py)
  - test: tests/conftest.py, tests/test_health.py
  - config: config.py, pyproject.toml, .env.example
  - app-factory: app.py
  - docs: docs/architecture.md
  - infra: migrations/README, __init__.py files
- Creates catalog.yaml with entries.

**Checkpoint:** catalog.yaml has entries for all 15 files. Each file has a
classification. No files are unclassified.

---

### Prompt 09b-B: Catalog Status (Baseline)

```text
/catalog status
```

**What Should Happen:**
- Reports catalog health:
  - Total files cataloged vs total files on disk
  - Classification breakdown (N models, N routes, N tests, etc.)
  - Any unclassified files
  - Last build timestamp
  - Staleness: any files modified since last catalog build

**Checkpoint:** Status shows 15/15 files cataloged with classification
distribution.

---

### Prompt 09b-C: Incremental Build After Auth Module

(Run this after Scenario 04 when auth is implemented.)

```text
I've added several new files for the authentication module. Update the
catalog to include them.

/catalog build
```

**What Should Happen:**
- Detects new files:
  - routes/auth.py → classified as "route"
  - services/auth_service.py → classified as "service"
  - utils/validators.py → classified as "validator" or "utility"
  - utils/decorators.py → classified as "decorator" or "utility"
  - tests/test_auth.py → classified as "test"
  - middleware/rate_limiter.py → classified as "middleware"
  - docs/api/auth.md → classified as "api-doc"
  - docs/adr/001-jwt-auth.md → classified as "adr"
- Updates catalog.yaml with new entries.
- Reports what was added and how it was classified.

**Checkpoint:** Catalog now has ~27 entries. New files correctly classified.
Status shows the updated distribution.

---

### Prompt 09b-D: Incremental Build After Multiple Modules

(Run after Scenario 08 when tasks, workspaces, comments are built.)

```text
Several modules have been added since the last catalog build. Rebuild to
catch up.

/catalog build
```

**What Should Happen:**
- Detects all new files from stages 2-5 (~35 new files).
- Classifies new categories that didn't exist before:
  - schema: marshmallow serialization files
  - mixin: model mixins
  - job: Celery background jobs
  - middleware: workspace context, rate limiter
  - event: event_bus.py
- Reports the full delta.

**Checkpoint:** Catalog now has 50-60 entries. New categories appear in the
classification breakdown. No unclassified files.

---

### Prompt 09b-E: Query by Classification

```text
Show me all model files in the project.

/catalog query "models"
```

**What Should Happen:**
- Returns all files classified as "model":
  - models/user.py
  - models/task.py
  - models/workspace.py
  - models/membership.py
  - models/comment.py
  - models/notification.py
  - models/mixins.py
- Each with its classification metadata.

**Checkpoint:** All model files returned. No false positives (routes aren't
listed). No false negatives (mixins.py is included).

---

### Prompt 09b-F: Query by Classification (Routes)

```text
/catalog query "routes"
```

**What Should Happen:**
- Returns: health.py, auth.py, tasks.py, workspaces.py, comments.py,
  notifications.py.
- Each with its endpoint summary if the catalog stores that metadata.

**Checkpoint:** All 6 route files returned.

---

### Prompt 09b-G: Query by Classification (Tests)

```text
/catalog query "tests"
```

**What Should Happen:**
- Returns all ~15 test files.
- Grouped or annotated by what they test.

**Checkpoint:** All test files returned. conftest.py included as test
infrastructure.

---

### Prompt 09b-H: Query by Purpose (Semantic)

```text
Which files handle user authentication? Not just the auth module — include
any file that touches auth: middleware, decorators, config, tests.

/catalog query "files related to authentication"
```

**What Should Happen:**
- Semantic query that crosses classification boundaries:
  - routes/auth.py (route)
  - services/auth_service.py (service)
  - utils/decorators.py (decorator — @require_auth)
  - middleware/rate_limiter.py (middleware — rate limits login)
  - tests/test_auth.py (test)
  - tests/test_auth_edge_cases.py (test)
  - models/user.py (model — has password methods)
  - config.py (config — JWT settings)
  - docs/api/auth.md (doc)
  - docs/adr/001-jwt-auth.md (adr)
- Returns files from multiple categories, ranked by relevance.

**Checkpoint:** At least 8 files returned spanning 5+ classifications.
User.py is included (password methods are auth-related). Config is included
(JWT settings).

---

### Prompt 09b-I: Query by Purpose (Cross-Cutting)

```text
/catalog query "files that handle HTTP request validation"
```

**What Should Happen:**
- Finds: validators.py, schemas/*.py, route files with validation logic,
  marshmallow schemas.
- Cross-cutting query that touches multiple modules.

**Checkpoint:** Results include both explicit validators and implicit
validation (marshmallow schemas that validate on deserialization).

---

### Prompt 09b-J: Query by Purpose (Infrastructure)

```text
/catalog query "configuration and environment files"
```

**What Should Happen:**
- Returns: config.py, pyproject.toml, .env.example, celery_app.py,
  catalog.yaml, project-standards.yaml.

**Checkpoint:** All config-type files returned including non-obvious ones
like celery_app.py.

---

### Prompt 09b-K: Query for Dependencies

```text
What files depend on the User model? What imports from models/user.py?

/catalog query "dependencies of user model"
```

**What Should Happen:**
- Traces imports/references to User:
  - services/auth_service.py (imports User for registration/login)
  - routes/auth.py (may reference User directly or through service)
  - models/__init__.py (re-exports User)
  - models/membership.py (ForeignKey to User)
  - tests/test_auth.py (creates User instances)
  - tests/conftest.py (may have User fixtures)
- Returns a dependency graph rooted at User.

**Checkpoint:** Dependency chain is accurate. Both direct imports and
indirect references are found.

---

### Prompt 09b-L: Query for Dependencies (Reverse)

```text
What does the task service depend on? What does task_service.py import?

/catalog query "what does task_service.py depend on"
```

**What Should Happen:**
- Traces outgoing dependencies:
  - models/task.py (Task model)
  - models/user.py (User for assignment)
  - app.py (db session)
  - Possibly utils/pagination.py

**Checkpoint:** Dependency list is accurate and complete.

---

### Prompt 09b-M: Status After Growth

```text
/catalog status
```

**What Should Happen:**
- Updated status showing:
  - 50-60 files cataloged
  - Classification breakdown:
    - model: 7, route: 6, service: 6, test: 15, config: 5,
      schema: 5, middleware: 3, job: 4, util: 4, doc: 25, adr: 5, etc.
  - Any new files not yet cataloged (if added since last build)
  - Build timestamp

**Checkpoint:** Status reflects the grown project accurately. Classification
distribution is reasonable.

---

### Prompt 09b-N: Catalog After File Moves (Refactoring)

```text
I moved validators.py from utils/ to a new validation/ directory and renamed
auth_service.py to authentication.py. Rebuild the catalog to handle these
moves.

/catalog build
```

**What Should Happen:**
- Detects:
  - utils/validators.py is gone → removed from catalog
  - validation/validators.py is new → classified
  - services/auth_service.py is gone → removed
  - services/authentication.py is new → classified as "service"
- Handles renames gracefully without losing classification history.

**Checkpoint:** Catalog reflects the new paths. No stale entries for old
paths. Classifications are preserved (validators.py is still a "validator"
at its new path).

---

### Prompt 09b-O: Query Empty/Sparse Categories

```text
Which parts of the codebase have no tests?

/catalog query "modules without test coverage"
```

**What Should Happen:**
- Cross-references test files against source files.
- Identifies modules with no corresponding test file:
  - If middleware/workspace_context.py has no test → flagged
  - If jobs/cleanup.py has no test → flagged
  - Utils may lack dedicated tests
- Reports coverage by module.

**Checkpoint:** List of source files without corresponding test files.

---

### Prompt 09b-P: Query for Patterns

```text
Show me all files that follow the blueprint pattern (Flask blueprints).

/catalog query "flask blueprint files"
```

**What Should Happen:**
- Finds all route files that define Blueprint objects.
- Returns: health.py, auth.py, tasks.py, workspaces.py, comments.py,
  notifications.py.
- May also find app.py where blueprints are registered.

**Checkpoint:** All blueprint files found. The pattern is identified
consistently.

---

### Prompt 09b-Q: Full Rebuild

```text
Do a complete catalog rebuild from scratch. Don't use the existing catalog —
rescan everything.

/catalog init
```

**What Should Happen:**
- Destroys existing catalog and rebuilds.
- All files reclassified from scratch.
- Result should match the incremental build (validates incremental accuracy).

**Checkpoint:** Fresh catalog matches the incremental one. No classification
drift between init and build approaches.
