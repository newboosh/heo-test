---
name: project-skeleton
description: Template for creating project-specific skills. Copy and customize for your Flask/Python project.
model: sonnet
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Project Skeleton Skill (Template)

This is a template for creating project-specific skills. Copy this file and customize for your project.

Use this to document:
- Architecture overview
- File structure
- Code patterns
- Testing requirements
- Deployment workflow

---

## When to Use

Reference this skill when working on a specific project. Project skills contain:
- Architecture decisions and rationale
- File structure conventions
- Common code patterns
- Testing requirements
- Deployment procedures

---

## Architecture Overview

**Tech Stack:**
- **Backend**: Flask 3.x, SQLAlchemy 2.x, Celery
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **Cache**: Redis
- **Auth**: Flask-Login, Flask-WTF (CSRF)
- **API**: REST with Marshmallow schemas
- **Testing**: pytest, pytest-flask, pytest-cov
- **Deployment**: [Gunicorn/Docker/etc.]

**Service Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  Jinja2 Templates + JavaScript                             │
│  CSP Nonce Required for Inline Scripts                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Backend                             │
│  Flask + SQLAlchemy + Celery                               │
│  Blueprints for Route Organization                         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Postgres │   │  Redis   │   │  Celery  │
        │ Database │   │  Cache   │   │  Worker  │
        └──────────┘   └──────────┘   └──────────┘
```

---

## File Structure

```
project/
├── app/
│   ├── __init__.py           # App factory
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── base.py
│   ├── api/                  # API blueprints
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── auth/                 # Authentication
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   ├── services/             # Business logic
│   │   └── user_service.py
│   ├── schemas/              # Marshmallow schemas
│   │   └── user_schema.py
│   ├── tasks/                # Celery tasks
│   │   └── email_tasks.py
│   ├── templates/            # Jinja2 templates
│   │   ├── base.html
│   │   └── auth/
│   └── static/               # Static files
│
├── tests/
│   ├── conftest.py           # Fixtures
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # Playwright E2E
│
├── migrations/               # Alembic migrations
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
│
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── Makefile                  # Common commands
└── .claude/                  # Claude Code config
```

---

## Code Patterns

### API Response Format

```python
from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class ApiResponse(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse[T]":
        return cls(success=False, error=error)

# Usage in routes
@bp.route('/api/users/<int:user_id>')
def get_user(user_id: int):
    user = UserService.get_by_id(user_id)
    if user is None:
        return jsonify(ApiResponse.fail("User not found").__dict__), 404
    return jsonify(ApiResponse.ok(user.to_dict()).__dict__)
```

### Service Layer Pattern

```python
# app/services/user_service.py
from typing import Optional
from app.models import User
from app import db

class UserService:
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        return db.session.get(User, user_id)

    @staticmethod
    def create(*, email: str, name: str, password: str) -> User:
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(user_id: int, **kwargs) -> Optional[User]:
        user = db.session.get(User, user_id)
        if user is None:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.session.commit()
        return user
```

### Schema Validation (Marshmallow)

```python
# app/schemas/user_schema.py
from marshmallow import Schema, fields, validate, validates, ValidationError

class CreateUserSchema(Schema):
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    password = fields.Str(required=True, validate=validate.Length(min=8))

    @validates('email')
    def validate_email_unique(self, value):
        if User.query.filter_by(email=value).first():
            raise ValidationError('Email already registered')

# Usage
schema = CreateUserSchema()
data = schema.load(request.get_json())  # Raises ValidationError if invalid
```

### Blueprint Organization

```python
# app/api/__init__.py
from flask import Blueprint

bp = Blueprint('api', __name__, url_prefix='/api')

from app.api import users, markets, auth  # noqa: E402, F401
```

### Celery Task Pattern

```python
# app/tasks/email_tasks.py
from celery import shared_task
from app import create_app

@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id: int):
    try:
        app = create_app()
        with app.app_context():
            user = User.query.get(user_id)
            if user:
                send_email(user.email, 'Welcome!', 'welcome.html')
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

---

## Testing Requirements

### Fixtures (conftest.py)

```python
import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email='test@example.com', name='Test')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user
```

### Test Structure

```python
# tests/unit/test_user_service.py
class TestUserService:
    def test_creates_user_with_valid_data(self, app):
        with app.app_context():
            user = UserService.create(
                email='new@example.com',
                name='New User',
                password='securepass123'
            )
            assert user.id is not None
            assert user.email == 'new@example.com'

    def test_hashes_password(self, app):
        with app.app_context():
            user = UserService.create(
                email='new@example.com',
                name='New User',
                password='securepass123'
            )
            assert user.password_hash != 'securepass123'
            assert user.check_password('securepass123')
```

### Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_user_service.py -v

# Run tests matching pattern
pytest -k "test_login" -v
```

---

## Deployment Workflow

### Pre-Deployment Checklist

- [ ] All tests passing (`pytest`)
- [ ] Type check passing (`mypy app/`)
- [ ] Lint check passing (`ruff check .`)
- [ ] No hardcoded secrets
- [ ] Database migrations ready (`flask db upgrade`)
- [ ] Environment variables documented

### Deployment Commands

```bash
# Run migrations
flask db upgrade

# Start production server
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"

# Start Celery worker
celery -A app.celery worker --loglevel=info
```

### Environment Variables

```bash
# .env.example
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your-secret-key-min-32-chars
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379/0
```

---

## Critical Rules

1. **Dignified Python** - Follow the 10 rules
2. **No print()** - Use logging instead
3. **TDD** - Write tests before implementation
4. **80% coverage** - Minimum requirement
5. **CSP nonce** - Required for all inline scripts/styles
6. **CSRF tokens** - Required for all forms
7. **Input validation** - Use Marshmallow schemas
8. **No bare except** - Always specify exception type

---

## Related Skills

- `backend-patterns.md` - Flask API patterns
- `tdd-workflow.md` - Test-driven development
- `security-review.md` - Security checklist
- `verification-loop.md` - Quality verification
