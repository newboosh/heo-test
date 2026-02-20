---
name: artifact-audit
description: Verify required artifacts exist (tests, docs, migrations). Used by QA Agent.
model: opus
allowed-tools: Read, Grep, Glob
---

# Artifact Audit

Check that all required artifacts accompany the code changes.

## Input

- **files**: Changed files to audit
- **change_type**: Type of change (feature, bugfix, refactor)

## Process

1. **Read project configuration**

   Check `.claude/project-standards.yaml` for custom paths:
   ```yaml
   # Example project-standards.yaml
   artifacts:
     models_path: "src/models/**/*.py"      # Default: app/models/**/*.py
     migrations_path: "db/migrations/"       # Default: migrations/versions/
     unit_tests_path: "tests/unit/"          # Default: tests/unit/
     integration_tests_path: "tests/integration/"  # Default: tests/integration/
     require_docstrings: true                # Default: true
     require_type_annotations: true          # Default: true (Python only)
   ```

2. **Identify required artifacts based on changed files**

   **Default mappings (override via project-standards.yaml):**

   | Changed | Required Artifact |
   |---------|-------------------|
   | `{models_path}` | Migration in `{migrations_path}` |
   | `{services_path}` | Tests in `{unit_tests_path}test_*.py` |
   | `{api_path}` | Tests in `{integration_tests_path}test_*.py` |
   | `{api_path}` | OpenAPI update if endpoints changed |
   | Public function | Docstring (if `require_docstrings: true`) |
   | Any code | Type annotations (if `require_type_annotations: true`) |

   **Language-specific defaults:**

   *Python (Flask/Django):*
   - models: `app/models/**/*.py`
   - services: `app/services/**/*.py`
   - api: `app/api/**/*.py`

   *TypeScript (NestJS/Express):*
   - models: `src/entities/**/*.ts`, `src/models/**/*.ts`
   - services: `src/services/**/*.ts`
   - api: `src/controllers/**/*.ts`, `src/routes/**/*.ts`

   *Go:*
   - models: `internal/models/*.go`, `pkg/models/*.go`
   - services: `internal/services/*.go`
   - api: `internal/handlers/*.go`, `cmd/api/*.go`

2. **Check for corresponding tests**
   ```
   # For each source file, find matching test file
   app/services/user_service.py → tests/unit/test_user_service.py
   app/api/users.py → tests/integration/test_users_api.py
   ```

3. **Check for migrations** (if models changed)
   ```
   # Compare model definitions to latest migration
   # Flag if schema change has no migration
   ```

4. **Check documentation artifacts**
   ```
   # README updated if public API changed
   # CHANGELOG updated for features/fixes
   # ADR if architectural decision made
   ```

## Output

```markdown
## Artifact Audit

### Files Changed
- `app/services/payment_service.py`
- `app/models/payment.py`

### Required Artifacts

| Artifact | Status | Location |
|----------|--------|----------|
| Unit tests | ✅ Present | `tests/unit/test_payment_service.py` |
| Migration | ❌ Missing | Expected in `migrations/versions/` |
| Docstrings | ⚠️ Partial | Missing on `process_refund()` |

### Missing
1. **Migration required** - `Payment` model changed, no migration found
2. **Docstring missing** - `process_refund()` at line 45
```

## Empty State Handling

**If no changed files provided:**
```markdown
## Artifact Audit

**Status:** No files to audit

No changed files were provided. Run with `diff-review` first to identify changes.
```

**If artifact mappings don't match project structure:**
```markdown
## Artifact Audit

**Status:** ⚠️ Unable to determine artifact requirements

Project structure doesn't match default conventions.

**Recommendation:** Add custom paths to `.claude/project-standards.yaml`:
\`\`\`yaml
artifacts:
  models_path: "your/models/path/**/*.py"
  unit_tests_path: "your/tests/path/"
\`\`\`
```

## Skill Dependencies

```
artifact-audit (this skill)
    │
    └── Reads .claude/project-standards.yaml (optional, for custom paths)
```

## Usage

**QA Agent:** Audit artifacts during review
