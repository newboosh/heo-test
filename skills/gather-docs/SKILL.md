---
name: gather-docs
description: Collect relevant documentation for a task. Used primarily by Context Agent.
model: haiku
allowed-tools: Read, Grep, Glob
---

# Gather Docs

Collect all documentation relevant to a task.

## Input

- **task**: Description of the work to be done
- **areas**: Affected areas of the codebase (optional)

## Process

1. **Find project-level docs**
   ```
   Glob: "README.md"
   Glob: "CONTRIBUTING.md"
   Glob: "docs/**/*.md"
   ```

2. **Find area-specific docs**
   ```
   Glob: "{area}/**/README.md"
   Glob: "{area}/**/*.md"
   ```

3. **Find relevant standards**
   - Consult `skills/standards-lookup/SKILL.md`
   - Read applicable standards from `standards/`

4. **Find config/spec files**
   ```
   Glob: "**/openapi*.yaml"     # API specs
   Glob: "**/pyproject.toml"    # Project config
   Glob: "**/.pre-commit*.yaml" # Hooks config
   ```

5. **Find ADRs**
   ```
   Glob: "**/adr/**/*.md"
   Glob: "**/decisions/**/*.md"
   ```

## Output

```markdown
## Relevant Documentation

### Standards
- `standards/api_standards.md` - REST conventions (RFC 7231)
- `standards/testing_standards.md` - pytest patterns

### Project Docs
- `docs/architecture.md` - System overview
- `app/api/README.md` - API module docs

### Specifications
- `docs/openapi.yaml` - API spec

### Decisions
- `docs/adr/0012-use-jwt.md` - Auth decision
```

## Empty State Handling

**If no documentation found:**
```markdown
## Relevant Documentation

### Status
No documentation found for: [task/areas]

### Checked Locations
- `README.md` - Not found or no relevant sections
- `docs/` - Directory not found
- `{area}/README.md` - Not found

### Recommendations
- This area may lack documentation
- Consider creating documentation as part of this task
- Check external wikis, Confluence, or Notion if used by team
```

## Skill Dependencies

```
gather-docs (this skill)
    │
    └── standards-lookup (to find applicable standards)
```

## Usage

**Context Agent:** Gather docs to include in context briefing
