# Refactor Clean

Safely identify and remove dead code with test verification.

## Process

1. Run dead code analysis tools:
   ```bash
   # Find unused code
   vulture app/ --min-confidence 80

   # Find unused imports
   autoflake --check -r app/

   # Ruff check for unused
   ruff check . --select F401,F841
   ```

2. Generate comprehensive report in `.reports/dead-code-analysis.md`

3. Categorize findings by severity:
   - **SAFE**: Unused imports, unused local variables
   - **CAUTION**: Unused private functions (_prefixed)
   - **DANGER**: Flask routes, Celery tasks, signal handlers

4. Propose safe deletions only

5. Before each deletion:
   - Run full test suite
   - Verify tests pass
   - Apply change
   - Re-run tests
   - Rollback if tests fail

6. Show summary of cleaned items

## Safety Rules

**NEVER DELETE:**
- Flask routes (`@app.route`, `@bp.route`)
- Celery tasks (`@celery.task`, `@shared_task`)
- CLI commands (`@app.cli.command`)
- SQLAlchemy models
- Signal handlers (`@event.listens_for`)
- Template filters
- Context processors

## Commands

```bash
# Full dead code analysis
vulture app/ --min-confidence 80

# Remove unused imports
autoflake --in-place --remove-all-unused-imports -r app/

# Check what would change
autoflake --check -r app/
```

Invokes the **refactor-cleaner** agent.

Never delete code without running tests first!
