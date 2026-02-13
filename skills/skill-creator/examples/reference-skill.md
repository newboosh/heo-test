---
name: coding-standards
description: Coding standards and conventions for this project. Use when writing or reviewing code.
---

# Coding Standards

Apply these standards to all code in this project.

## Python Standards

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Maximum line length: 88 characters (Black default)
- Use f-strings for string formatting

## Naming Conventions

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

## Documentation

- All public functions need docstrings
- Use Google-style docstrings
- Include type information in docstrings

## Error Handling

- Use specific exception types
- Never use bare `except:`
- Log errors with context
