# TaskHive Architecture

## Overview

TaskHive is a REST API for collaborative task management.

## Stack

- Python 3.11
- Flask (web framework)
- SQLAlchemy (ORM)
- Celery + Redis (background jobs)
- JWT (authentication)
- pytest (testing)

## Layers

```
routes/ → services/ → models/
```

Routes handle HTTP. Services contain business logic. Models define data.

## Modules (planned)

- Authentication (JWT-based login/register)
- Tasks (CRUD, assignment, priorities, due dates)
- Workspaces (multi-tenant team isolation)
- Comments (threaded discussion on tasks)
- Notifications (real-time updates — transport TBD)
- Background jobs (email digests, report generation)
