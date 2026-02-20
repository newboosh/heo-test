---
name: prereq-check
description: Verify prerequisites and dependencies before starting work. Used by Context Agent.
model: haiku
allowed-tools: Read, Bash, Grep, Glob
---

# Prerequisite Check

Verify that required setup, dependencies, and configurations are in place.

## Input

- **task**: Description of the work to be done
- **type**: Type of work (api, database, test, frontend)

## Process

1. **Check for required files based on task type**

   **API work:**
   ```
   Glob: "app/api/__init__.py"     # API module exists
   Glob: "**/openapi*.yaml"        # API spec exists
   ```

   **Database work:**
   ```
   Glob: "migrations/versions/*.py" # Migrations exist
   Glob: "app/models/__init__.py"   # Models module exists
   ```

   **Test work:**
   ```
   Glob: "tests/conftest.py"        # Test config exists
   Glob: "pytest.ini"               # Pytest config
   ```

2. **Check dependencies**
   ```
   Read: "requirements.txt" or "pyproject.toml"
   # Verify required packages are listed
   ```

3. **Check configurations**
   ```
   Glob: ".env.example"             # Env template exists
   Glob: "config/*.py"              # Config modules
   ```

4. **Check for existing patterns**
   - Use `find-patterns` skill to verify conventions exist

## Output

```markdown
## Prerequisite Check

### Ready
- [x] API module exists
- [x] Test framework configured
- [x] Required dependencies installed

### Missing
- [ ] No OpenAPI spec found - create `docs/openapi.yaml`
- [ ] Missing pytest-cov in requirements

### Warnings
- `.env.example` exists but is outdated (missing NEW_VAR)
```

## Empty State Handling

**If prerequisites cannot be determined:**
```markdown
## Prerequisite Check

### Status
Unable to determine prerequisites for: [task]

### Reason
- Task type not recognized
- No standard project structure detected

### Recommendations
- Specify task type explicitly (api, database, test, frontend)
- Ensure project follows conventional structure
- Add `.claude/project-standards.yaml` with custom paths
```

## Skill Dependencies

```
prereq-check (this skill)
    │
    └── find-patterns (to check for existing conventions)
```

## Usage

**Context Agent:** Check prerequisites before providing context briefing
