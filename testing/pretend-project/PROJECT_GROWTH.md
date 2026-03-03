# TaskHive — Project Growth Plan

How the pretend project evolves through the scenarios. The scaffold starts
minimal. Each scenario adds files. By the end, the project is ~80+ files
across 6 modules with full documentation, giving the catalog and librarian
rich material to work with.

This file is the source of truth for what SHOULD exist at each stage. The
test repo builds these files by following the scenario prompts.

---

## Stage 0: Scaffold (Scenario 00)

15 files. Bare Flask project.

```
src/taskhive/
├── __init__.py
├── app.py
├── config.py
├── models/
│   ├── __init__.py
│   └── user.py
├── routes/
│   ├── __init__.py
│   └── health.py
├── services/
│   └── __init__.py
└── utils/
    └── __init__.py
tests/
├── conftest.py
└── test_health.py
docs/
└── architecture.md
migrations/
└── README
pyproject.toml
.env.example
```

**Catalog classifications at this stage:**
- model: user.py
- route: health.py
- config: config.py, app.py, pyproject.toml
- test: test_health.py, conftest.py
- docs: architecture.md
- infra: migrations/README, .env.example, __init__.py files

---

## Stage 1: Auth Module (Scenarios 04-05)

+12 files. Authentication fully implemented via TDD.

```
src/taskhive/
├── routes/
│   └── auth.py                    # NEW: register, login endpoints
├── services/
│   └── auth_service.py            # NEW: registration, login logic
├── utils/
│   ├── validators.py              # NEW: email, password validation
│   └── decorators.py              # NEW: @require_auth decorator
├── middleware/
│   ├── __init__.py                # NEW
│   └── rate_limiter.py            # NEW: login rate limiting
tests/
├── test_auth.py                   # NEW: registration, login tests
├── test_auth_edge_cases.py        # NEW: token expiry, malformed tokens
├── test_validators.py             # NEW: validation unit tests
docs/
├── api/
│   └── auth.md                    # NEW: auth endpoint docs
└── adr/
    └── 001-jwt-auth.md            # NEW: ADR for JWT choice
```

**New catalog classifications:**
- middleware: rate_limiter.py
- validator: validators.py
- decorator: decorators.py
- api-doc: api/auth.md
- adr: adr/001-jwt-auth.md

---

## Stage 2: Task CRUD Module (Scenarios 04, 08)

+14 files. Core task management.

```
src/taskhive/
├── models/
│   ├── task.py                    # NEW: Task model
│   └── mixins.py                  # NEW: TimestampMixin, SoftDeleteMixin
├── routes/
│   └── tasks.py                   # NEW: CRUD endpoints
├── services/
│   └── task_service.py            # NEW: task business logic
├── schemas/
│   ├── __init__.py                # NEW
│   ├── task_schema.py             # NEW: marshmallow serialization
│   └── common.py                  # NEW: shared pagination schema
├── utils/
│   └── pagination.py              # NEW: cursor-based pagination
tests/
├── test_tasks.py                  # NEW: CRUD tests
├── test_task_model.py             # NEW: model unit tests
├── test_task_schema.py            # NEW: serialization tests
docs/
├── api/
│   └── tasks.md                   # NEW: task endpoint docs
└── adr/
    └── 002-soft-delete.md         # NEW: ADR for soft delete strategy
```

**New catalog classifications:**
- schema: task_schema.py, common.py
- mixin: mixins.py
- util: pagination.py

---

## Stage 3: Workspace Module (Scenarios 03, 08)

+11 files. Multi-tenant workspace isolation.

```
src/taskhive/
├── models/
│   ├── workspace.py               # NEW: Workspace model
│   └── membership.py              # NEW: user-workspace relation
├── routes/
│   └── workspaces.py              # NEW: workspace CRUD, invite, members
├── services/
│   └── workspace_service.py       # NEW: workspace logic, access control
├── schemas/
│   └── workspace_schema.py        # NEW: workspace serialization
├── middleware/
│   └── workspace_context.py       # NEW: inject workspace from header/URL
tests/
├── test_workspaces.py             # NEW
├── test_workspace_access.py       # NEW: permission/isolation tests
docs/
├── api/
│   └── workspaces.md              # NEW
├── adr/
│   └── 003-multi-tenancy.md       # NEW: ADR for tenant isolation approach
└── guides/
    └── workspace-setup.md         # NEW: how to create and manage workspaces
```

**New catalog classifications:**
- middleware: workspace_context.py
- guide: workspace-setup.md

---

## Stage 4: Comments Module (Scenario 08)

+8 files. Threaded comments on tasks.

```
src/taskhive/
├── models/
│   └── comment.py                 # NEW: Comment model (self-referencing FK)
├── routes/
│   └── comments.py                # NEW: CRUD nested under tasks
├── services/
│   └── comment_service.py         # NEW: threading, mentions
├── schemas/
│   └── comment_schema.py          # NEW
tests/
├── test_comments.py               # NEW
docs/
├── api/
│   └── comments.md                # NEW
├── adr/
│   └── 004-threaded-comments.md   # NEW: flat vs threaded vs nested
└── guides/
    └── commenting.md              # NEW: usage guide
```

---

## Stage 5: Notifications Module (Scenarios 02, 08)

+10 files. Real-time notifications (transport decided by arch-debate).

```
src/taskhive/
├── models/
│   └── notification.py            # NEW: Notification model
├── routes/
│   └── notifications.py           # NEW: list, mark-read, SSE stream
├── services/
│   ├── notification_service.py    # NEW: create, dispatch
│   └── event_bus.py               # NEW: internal pub/sub
├── schemas/
│   └── notification_schema.py     # NEW
tests/
├── test_notifications.py          # NEW
├── test_event_bus.py              # NEW: pub/sub unit tests
docs/
├── api/
│   └── notifications.md           # NEW
└── adr/
    └── 005-notification-transport.md  # NEW: from arch-debate in scenario 02
```

---

## Stage 6: Background Jobs (Scenarios 08, 10)

+9 files. Celery-based async processing.

```
src/taskhive/
├── celery_app.py                  # NEW: Celery factory
├── jobs/
│   ├── __init__.py                # NEW
│   ├── email_digest.py            # NEW: daily email summary job
│   ├── report_generator.py        # NEW: export tasks to CSV/PDF
│   └── cleanup.py                 # NEW: purge old notifications
tests/
├── test_jobs.py                   # NEW: job unit tests
├── test_celery_integration.py     # NEW: Celery integration tests
docs/
├── guides/
│   └── background-jobs.md         # NEW: how to add new jobs
└── ops/
    └── celery-deployment.md       # NEW: running workers in production
```

**New catalog classifications:**
- job: email_digest.py, report_generator.py, cleanup.py
- ops-doc: celery-deployment.md

---

## Stage 7: Documentation Buildout (Scenario 09)

+12 files. Full documentation suite for librarian to manage.

```
docs/
├── README.md                      # NEW: docs index
├── architecture.md                # UPDATED: no longer says "planned"
├── api/
│   ├── README.md                  # NEW: API docs index
│   ├── auth.md                    # EXISTS from stage 1
│   ├── tasks.md                   # EXISTS from stage 2
│   ├── workspaces.md              # EXISTS from stage 3
│   ├── comments.md                # EXISTS from stage 4
│   ├── notifications.md           # EXISTS from stage 5
│   └── errors.md                  # NEW: error code reference
├── adr/
│   ├── README.md                  # NEW: ADR index
│   ├── 001-jwt-auth.md            # EXISTS
│   ├── 002-soft-delete.md         # EXISTS
│   ├── 003-multi-tenancy.md       # EXISTS
│   ├── 004-threaded-comments.md   # EXISTS
│   └── 005-notification-transport.md  # EXISTS
├── guides/
│   ├── getting-started.md         # NEW: quickstart for new devs
│   ├── workspace-setup.md         # EXISTS
│   ├── commenting.md              # EXISTS
│   ├── background-jobs.md         # EXISTS
│   └── testing.md                 # NEW: how to run tests, write tests
├── ops/
│   ├── deployment.md              # NEW: production deployment
│   ├── celery-deployment.md       # EXISTS
│   ├── monitoring.md              # NEW: health checks, logging
│   └── database.md               # NEW: migrations, backups
├── contributing.md                # NEW: contribution guidelines
├── changelog.md                   # NEW: version history
└── diagrams/
    ├── data-model.md              # NEW: ER diagram
    ├── request-flow.md            # NEW: request lifecycle
    └── module-dependencies.md     # NEW: module dependency graph
```

---

## Final State: Full Project (~80+ files)

```
src/taskhive/             ~35 source files
├── __init__.py
├── app.py
├── config.py
├── celery_app.py
├── models/               (7 files: user, task, workspace, membership,
│                          comment, notification, mixins)
├── routes/               (6 files: health, auth, tasks, workspaces,
│                          comments, notifications)
├── services/             (6 files: auth, task, workspace, comment,
│                          notification, event_bus)
├── schemas/              (5 files: task, workspace, comment,
│                          notification, common)
├── middleware/            (3 files: rate_limiter, workspace_context, init)
├── jobs/                 (4 files: email_digest, report_generator,
│                          cleanup, init)
└── utils/                (4 files: validators, decorators, pagination, init)

tests/                    ~15 test files
├── conftest.py
├── test_health.py
├── test_auth.py
├── test_auth_edge_cases.py
├── test_validators.py
├── test_tasks.py
├── test_task_model.py
├── test_task_schema.py
├── test_workspaces.py
├── test_workspace_access.py
├── test_comments.py
├── test_notifications.py
├── test_event_bus.py
├── test_jobs.py
└── test_celery_integration.py

docs/                     ~25 doc files
├── README.md
├── architecture.md
├── contributing.md
├── changelog.md
├── api/                  (7 files)
├── adr/                  (6 files)
├── guides/               (5 files)
├── ops/                  (4 files)
└── diagrams/             (3 files)

config/                   ~5 files
├── pyproject.toml
├── .env.example
├── catalog.yaml
├── project-standards.yaml
└── migrations/
```

**Total: ~80 files across 6 modules, 5 ADRs, 7 API docs, 5 guides,
4 ops docs, 3 diagrams, 15 test files.**

This gives the catalog ~80 entries to classify across 15+ categories,
and the librarian ~25 documentation files to audit, cross-reference,
and maintain.
