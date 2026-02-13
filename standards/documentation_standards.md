# Documentation Standards

Canonical specifications for documentation. References authoritative standards where applicable.

---

## Docstrings

**Standard:** Google Python Style Guide
**Reference:** google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
**Also:** PEP 257 — Docstring Conventions

### Format
```python
def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
    """Calculate total price including tax.

    Args:
        items: List of items to sum.
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%).

    Returns:
        Total price with tax applied.

    Raises:
        ValueError: If tax_rate is negative.
    """
```

### Sections (in order)
1. Summary line
2. Extended description (optional)
3. Args
4. Returns
5. Raises
6. Example (optional)

### When Required
| Element | Required |
|---------|----------|
| Public functions | Yes |
| Public classes | Yes |
| Public methods | Yes |
| Modules | Yes |
| Private functions | No (unless complex) |

---

## Inline Comments

**Reference:** *Clean Code* (Martin, 2008); PEP 8

### When to Comment
| Comment | Don't Comment |
|---------|---------------|
| Why (decisions) | What (obvious code) |
| Workarounds | Every line |
| Business rules | Simple operations |
| Regex patterns | Self-documenting code |

### TODO Format
```python
# TODO(username): Description - Issue #123
# FIXME: Known bug description - Issue #456
# HACK: Workaround explanation
```

---

## README

**Reference:** Make a README (makeareadme.com); GitHub documentation guidelines

### Required Sections
```markdown
# Project Name
Brief description.

## Quick Start
## Features
## Installation
## Usage
## Configuration
## Development
## Testing
## License
```

---

## Architecture Decision Records (ADR)

**Standard:** ADR format
**Reference:** adr.github.io; *Documenting Software Architectures* (Clements et al., 2010)

### Format
```markdown
# NNNN. Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What motivates this decision?

## Decision
What are we doing?

## Consequences
What becomes easier/harder?
```

---

## Changelog

**Standard:** Keep a Changelog
**Reference:** keepachangelog.com v1.1.0; Semantic Versioning (semver.org)

### Format
```markdown
## [Unreleased]

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
```

---

## API Documentation

**Standard:** OpenAPI Specification 3.0
**Reference:** spec.openapis.org/oas/v3.0.3

For REST APIs, maintain `openapi.yaml` with:
- Endpoint paths and methods
- Request/response schemas
- Authentication requirements
- Example payloads

---

## Verification Checklist

- [ ] Docstrings follow Google style
- [ ] All public APIs documented
- [ ] Args/Returns/Raises complete
- [ ] No stale TODOs without issues
- [ ] README has required sections
