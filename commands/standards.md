# Standards Lookup

Look up the correct standard for any work type, respecting project choices.

## Usage

```
/standards <work type>
```

## Lookup Order

```
/standards erd
    │
    ├─► Read .claude/project-standards.yaml
    │       → diagrams.erd = "chen"
    │
    └─► Return Chen notation (not default Crow's Foot)
```

If no project config exists or standard not specified, returns the default.

## Project Config

Location: `.claude/project-standards.yaml`

```yaml
diagrams:
  erd: chen  # Override default
```

## Quick Reference (Defaults)

| Query | Default Standard | Reference |
|-------|------------------|-----------|
| `dfd` | Yourdon-DeMarco | DeMarco, 1979 |
| `sequence` | UML 2.5 | OMG formal/2017-12-05 |
| `erd` | Crow's Foot | Martin, 1990 |
| `flowchart` | ISO 5807 | ISO 5807:1985 |
| `architecture` | C4 Model | c4model.com |
| `unit test` | pytest + AAA | xUnit Patterns |
| `e2e` | Playwright + POM | Playwright docs |
| `docstring` | Google style | PEP 257 |
| `api` | REST | RFC 7231 |
| `response` | JSON + RFC 7807 | RFC 7807 |
| `dates` | ISO 8601 | RFC 3339 |
| `python` | PEP 8 | peps.python.org |
| `types` | PEP 484 | peps.python.org |
| `commit` | Conventional Commits | conventionalcommits.org |

## Output

- Project's chosen standard (or default)
- Authoritative reference
- Key rules
- Link to full specification in `standards/`

Uses the **standards-lookup** skill internally to find and return the applicable standard.
