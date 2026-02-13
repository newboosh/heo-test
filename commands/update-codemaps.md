# Update Codemaps

Analyze the codebase structure and update architecture documentation.

## Process

1. Scan all source files for imports, classes, and functions
2. Generate token-lean codemaps:
   - `docs/CODEMAPS/INDEX.md` - Overview
   - `docs/CODEMAPS/app-structure.md` - Application structure
   - `docs/CODEMAPS/api-routes.md` - Flask routes
   - `docs/CODEMAPS/models.md` - SQLAlchemy models
   - `docs/CODEMAPS/services.md` - Business logic
   - `docs/CODEMAPS/tasks.md` - Celery tasks

3. Calculate diff percentage from previous version
4. If changes > 30%, request user approval before updating
5. Add freshness timestamp to each codemap

## Commands

```bash
# List all Flask routes
flask routes

# Find all Python modules
find app/ -name "*.py" -type f

# Extract function definitions
grep -rn "^def \|^async def " app/ --include="*.py"

# Extract class definitions
grep -rn "^class " app/ --include="*.py"

# Find Celery tasks
grep -rn "@celery.task\|@shared_task" app/ --include="*.py"

# Find Flask blueprints
grep -rn "Blueprint(" app/ --include="*.py"
```

## Codemap Format

```markdown
# [Area] Codemap

**Last Updated:** YYYY-MM-DD
**Entry Points:** [list of main files]

## Structure
[Directory tree]

## Key Modules
| Module | Purpose | Key Functions |
|--------|---------|---------------|

## Data Flow
[Description]
```

Invokes the **doc-updater** agent.

Focus on high-level structure, not implementation details.
