# Conventional Commits Full Specification

Based on [Conventional Commits v1.0.0](https://www.conventionalcommits.org/)

## Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature for the user | `feat: add user authentication` |
| `fix` | Bug fix for the user | `fix: resolve login timeout issue` |
| `docs` | Documentation only changes | `docs: update API reference` |
| `style` | Formatting, missing semicolons, etc. (no code change) | `style: fix indentation in models` |
| `refactor` | Code change that neither fixes a bug nor adds a feature | `refactor: extract email validation logic` |
| `perf` | Performance improvement | `perf: optimize database queries` |
| `test` | Adding or correcting tests | `test: add unit tests for auth module` |
| `build` | Changes to build system or dependencies | `build: update requirements.txt` |
| `ci` | Changes to CI configuration | `ci: add GitHub Actions workflow` |
| `chore` | Other changes that don't modify src or test files | `chore: update .gitignore` |
| `revert` | Reverts a previous commit | `revert: revert feat: add user auth` |

## Scope

Optional context for the change:

```
feat(auth): add OAuth2 support
fix(api): handle null response
refactor(models): simplify User class
```

Common scopes for this project:
- `auth` - Authentication, 2FA, password reset
- `api` - API endpoints
- `models` - Database models
- `rag` - RAG system, LLM orchestration
- `celery` - Background tasks
- `ui` - Frontend templates
- `db` - Database operations

## Description

- Use imperative, present tense: "add" not "added" or "adds"
- Don't capitalize first letter
- No period at the end
- Keep under 72 characters

### Good Examples
```
feat: add password reset functionality
fix: prevent race condition in token refresh
refactor: simplify error handling in API layer
```

### Bad Examples
```
feat: Added password reset functionality  # Past tense, capitalized
fix: Prevents race condition.             # Third person, period
refactor: Simplifying error handling      # Gerund
```

## Body

- Use imperative, present tense
- Include motivation for the change
- Contrast with previous behavior

```
fix: prevent race condition in token refresh

The previous implementation allowed multiple concurrent refresh
requests, causing token invalidation. Now uses a mutex lock to
ensure only one refresh occurs at a time.
```

## Footer

### Breaking Changes

```
feat(api)!: change response format

BREAKING CHANGE: API now returns ISO 8601 dates instead of Unix timestamps.
Clients must update their date parsing logic.
```

Or with `!` in the type line:

```
feat!: drop support for Python 3.8
```

### Issue References

```
fix: resolve login timeout

Fixes #123
Closes #456
Refs #789
```

## Full Examples

### Simple Feature
```
feat(auth): add two-factor authentication support
```

### Bug Fix with Body
```
fix(api): handle null user profile gracefully

Previously, the API would crash when a user had no profile set.
Now returns a default empty profile object.

Fixes #234
```

### Breaking Change
```
feat(models)!: rename User.email_verified to User.is_email_verified

BREAKING CHANGE: Database migration required. Run:
  flask db upgrade

All code referencing email_verified must be updated to is_email_verified.

Refs #567
```

### Revert
```
revert: feat(auth): add OAuth2 support

This reverts commit abc1234.

OAuth2 integration caused issues with existing session management.
Will reimplement with proper session handling.
```

## Git Safety Rules

These rules are MANDATORY for all commits:

1. **Never use `--no-verify`** - Pre-commit hooks exist for quality control
2. **Never push directly to `main`** - Always use feature branches and PRs
3. **Never force push to protected branches** - This destroys history

## Co-Author Attribution

When Claude assists with code:

```
feat: implement user dashboard

Co-Authored-By: Claude <noreply@anthropic.com>
```
