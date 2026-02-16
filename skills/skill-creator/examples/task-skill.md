---
name: create-migration
description: Create a database migration for schema changes
disable-model-invocation: true
argument-hint: [migration-name]
---

# Create Database Migration

Create an Alembic migration for: $ARGUMENTS

## Steps

1. **Analyze changes needed**
   - Review model changes
   - Identify new tables, columns, indexes

2. **Generate migration**
   ```bash
   flask db migrate -m "$ARGUMENTS"
   ```

3. **Review generated migration**
   - Check upgrade() function
   - Check downgrade() function
   - Verify reversibility

4. **Test migration**
   ```bash
   flask db upgrade
   flask db downgrade
   flask db upgrade
   ```

5. **Commit migration**
   - Add migration file to git
   - Include descriptive commit message

## Output

Report:
- Migration file path
- Changes included
- Test results
