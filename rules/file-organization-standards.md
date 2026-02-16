# File Organization Standards

**Purpose:** Define clear standards for file placement, naming, and organization for this Flask/Python project.

## Directory Structure

### Root Directory
**Allowed Files:**
- `README.md` - Project overview
- `CLAUDE.md` - AI assistant instructions (symlink to .claude/)
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Python project configuration
- `Makefile` - Build/test commands
- `docker-compose.yml` - Docker configuration
- `.env` (gitignored) - Environment variables
- `.gitignore` - Git ignore rules

**Prohibited in Root:**
- Test files → `tests/`
- Documentation → `docs/`
- Scripts → `scripts/`
- Application code → `app/`

### Application Code (`app/`)

```
app/
├── __init__.py          # Flask app factory
├── models/              # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   └── ...
├── auth/                # Authentication module
│   ├── __init__.py
│   ├── routes.py
│   ├── services.py
│   └── ...
├── rag/                 # RAG system
│   ├── __init__.py
│   ├── retriever.py
│   ├── orchestrator.py
│   └── ...
├── utils/               # Shared utilities
│   ├── __init__.py
│   └── ...
├── templates/           # Jinja2 templates
│   └── ...
└── static/              # Static assets
    └── ...
```

### Tests (`tests/`)

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   ├── test_models.py
│   ├── test_auth.py
│   └── ...
├── integration/         # Integration tests
│   └── ...
└── e2e/                 # End-to-end tests
    └── ...
```

**Naming:** `test_<module_name>.py`

### Scripts (`scripts/`)

```
scripts/
├── deployment/          # Deploy scripts
├── database/            # DB management
├── migrations/          # Migration scripts
└── utils/               # Utility scripts
```

### Documentation (`docs/`)

```
docs/
├── api/                 # API documentation
├── architecture/        # System design docs
├── guides/              # How-to guides
├── component_docs/      # Component-specific docs
└── archived/            # Historical docs
```

### Claude Code Configuration (`.claude/`)

```
.claude/
├── CLAUDE.md            # Main instructions
├── settings.json        # Claude settings
├── commands/            # Slash commands
├── skills/              # Skills
├── agents/              # Agent definitions
├── hooks/               # Hook scripts
└── rules/               # Rules and standards
```

## Naming Conventions

### Python Files
**Standard:** `snake_case.py`

```
✅ user_service.py
✅ test_authentication.py
✅ oauth_handler.py
❌ UserService.py (PascalCase)
❌ user-service.py (hyphens)
```

### Documentation Files
**Standard:** `lowercase-with-hyphens.md`

```
✅ authentication-guide.md
✅ api-reference.md
✅ database-schema.md
❌ AUTHENTICATION_GUIDE.md (uppercase)
❌ authentication_guide.md (underscores)
```

**Exception:** Root files may use UPPERCASE (`README.md`, `CLAUDE.md`)

### Test Files
**Standard:** `test_<module>.py`

```
✅ test_user_model.py
✅ test_auth_routes.py
❌ user_model_test.py (suffix style)
❌ TestUserModel.py (PascalCase)
```

### Directories
**Standard:** `lowercase` or `snake_case`

```
✅ app/models/
✅ scripts/migrations/
✅ app/services/
❌ app/Models/ (PascalCase)
❌ app/my-service/ (hyphens in code dirs)
```

## File Placement Decision Tree

### For New Python Code

```
Is it a test?
├─ Yes: What type?
│  ├─ Unit test → tests/unit/test_<name>.py
│  ├─ Integration → tests/integration/test_<name>.py
│  └─ E2E → tests/e2e/test_<name>.py
│
└─ No: Is it Flask application code?
   ├─ Yes: What type?
   │  ├─ Model → app/models/<name>.py
   │  ├─ Route/API → app/<module>/routes.py
   │  ├─ Business logic → app/<module>/services.py
   │  ├─ Shared utility → app/utils/<name>.py
   │  ├─ RAG component → app/rag/<name>.py
   │  └─ Auth component → app/auth/<name>.py
   │
   └─ No: Is it a script/tool?
      ├─ Yes: What purpose?
      │  ├─ Database → scripts/database/<name>.py
      │  ├─ Deployment → scripts/deployment/<name>.py
      │  ├─ Migrations → scripts/migrations/<name>.py
      │  └─ General → scripts/<name>.py
      │
      └─ No → Reconsider if needed
```

### For New Documentation

```
Is it API documentation?
├─ Yes → docs/api/<name>.md
│
└─ No: Is it a how-to guide?
   ├─ Yes → docs/guides/<name>.md
   │
   └─ No: Is it architecture/design?
      ├─ Yes → docs/architecture/<name>.md
      │
      └─ No: Is it component-specific?
         ├─ Yes → docs/component_docs/<component>/<name>.md
         │
         └─ No: Is it historical/completed?
            ├─ Yes → docs/archived/<category>/<name>.md
            └─ No → docs/<appropriate-category>/<name>.md
```

## Test-to-Source Mapping

| Source Module | Test Location |
|---------------|---------------|
| `app/models/user.py` | `tests/unit/test_user_model.py` |
| `app/auth/routes.py` | `tests/unit/test_auth_routes.py` |
| `app/auth/services.py` | `tests/unit/test_auth_services.py` |
| `scripts/migrations/utils.py` | `tests/unit/test_migration_utils.py` |

**Rule:** Every module in `app/` should have a corresponding test file.

## Import Organization

**Standard order (enforced by ruff):**
1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import os
from datetime import datetime

# Third-party
from flask import Flask, request
from sqlalchemy import Column, Integer

# Local application
from app.models import User
from app.utils import format_date
```

## Docstring Standards

**All public functions must have docstrings:**

```python
def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate a user by email and password.

    Args:
        email: User's email address
        password: Plain text password to verify

    Returns:
        User object if authentication succeeds, None otherwise

    Raises:
        ValueError: If email format is invalid
    """
```

**All modules should have module-level docstrings:**

```python
"""Authentication services for user login and session management.

This module provides the core authentication logic including:
- Password verification
- Session token generation
- 2FA validation
"""
```

## Archive Guidelines

### When to Archive

- Feature branch merged and documented
- Migration completed and verified
- Documentation superseded by newer version
- Historical context valuable but not current

### Archive Structure

```
docs/archived/
├── migrations/          # Completed migration docs
├── features/            # Completed feature docs
└── deprecated/          # Deprecated approach docs
```

### Archive File Header

```markdown
---
archived: 2025-01-15
reason: Feature merged to main, superseded by X
related: docs/current-feature.md
---
```

## Enforcement

### Automated
- **ruff**: Import ordering, naming conventions
- **mypy**: Type hints presence
- **Pre-commit hooks**: File location validation

### Manual
- **Code review**: Check file placement
- **Librarian audit**: Quarterly organization check
- **PR checklist**: "Files in correct location?"

## Quick Reference

| File Type | Location | Naming |
|-----------|----------|--------|
| Flask route | `app/<module>/routes.py` | snake_case |
| SQLAlchemy model | `app/models/<name>.py` | snake_case |
| Unit test | `tests/unit/test_<name>.py` | test_ prefix |
| Utility script | `scripts/<name>.py` | snake_case |
| API docs | `docs/api/<name>.md` | hyphen-case |
| Guide | `docs/guides/<name>.md` | hyphen-case |
