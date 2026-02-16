# Code Style Standards

Canonical specifications for code style. References authoritative standards.

---

## Python Style

**Standard:** PEP 8
**Reference:** peps.python.org/pep-0008/
**Also:** Google Python Style Guide

### Formatting
| Rule | Value |
|------|-------|
| Line length | 100 chars |
| Indentation | 4 spaces |
| Quotes | Double |
| Trailing commas | Yes (multi-line) |

### Import Order
**Reference:** PEP 8; isort defaults

```python
# 1. Standard library
import os
from datetime import datetime

# 2. Third-party
import flask
from pydantic import BaseModel

# 3. Local
from app.models import User
```

### Naming
**Reference:** PEP 8 Naming Conventions

| Element | Convention |
|---------|------------|
| Module | `snake_case` |
| Class | `PascalCase` |
| Function | `snake_case` |
| Constant | `UPPER_SNAKE` |
| Private | `_leading_underscore` |

---

## Type Annotations

**Standard:** PEP 484, PEP 604
**Reference:** peps.python.org/pep-0484/; mypy documentation

```python
# Python 3.9+ generics
def get_items() -> list[Item]: ...
def get_map() -> dict[str, int]: ...

# Union types (3.10+)
def parse(value: str | int) -> float: ...

# Optional
def find(id: int) -> Optional[User]: ...
```

### Required On
- All public function parameters
- All public function returns
- Class attributes

---

## Error Handling

**Reference:** PEP 8; *Effective Python* (Slatkin)

### LBYL Pattern (Look Before You Leap)
```python
# Preferred
if user_id in cache:
    return cache[user_id]
return fetch_user(user_id)

# Avoid EAFP in most cases
try:
    return cache[user_id]
except KeyError:
    return fetch_user(user_id)
```

### Never Swallow Exceptions
```python
# Bad
except Exception:
    pass

# Good
except SpecificError as e:
    logger.warning(f"Non-critical: {e}")
    return default
```

---

## Dignified Python Rules

Project-specific rules beyond PEP 8:

1. **LBYL over EAFP** — Check before acting
2. **Never swallow exceptions** — Always handle or propagate
3. **Magic methods O(1)** — `__len__`, `__bool__` must be constant time
4. **Check .exists() before .resolve()** — Path validation
5. **Defer import-time computation** — Lazy initialization
6. **Verify casts at runtime** — Validate before type narrowing
7. **Literal types for fixed values** — `Literal["a", "b"]`
8. **Variables close to use** — Declare near first reference
9. **Keyword-only for 5+ params** — Use `*` separator
10. **No mutable defaults** — Use `None` + initialization

---

## File Structure

**Reference:** PEP 8; Google Python Style Guide

```python
"""Module docstring."""

# Imports
import ...

# Constants
MAX_RETRIES = 3

# Type aliases
UserId: TypeAlias = int

# Exceptions
class ModuleError(Exception): ...

# Classes
class MainClass: ...

# Functions
def main_function(): ...
```

---

## Verification Checklist

- [ ] Import order correct
- [ ] Naming conventions followed
- [ ] Type annotations present
- [ ] No bare except clauses
- [ ] No swallowed exceptions
- [ ] LBYL pattern used
- [ ] No mutable defaults
- [ ] Keyword-only for 5+ params
