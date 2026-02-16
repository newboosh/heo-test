# Update Documentation

Sync documentation from source-of-truth.

## Process

1. Read `pyproject.toml` or `setup.py`:
   - Extract project metadata
   - Document available scripts/commands

2. Read `.env.example`:
   - Extract all environment variables
   - Document purpose and format

3. Read `Makefile`:
   - Document available make targets
   - Include descriptions

4. Generate/update `docs/SETUP.md` with:
   - Installation steps
   - Environment setup
   - Development workflow
   - Available commands

5. Generate/update `docs/RUNBOOK.md` with:
   - Deployment procedures
   - Common issues and fixes
   - Rollback procedures

6. Identify obsolete documentation:
   - Find docs not modified in 90+ days
   - List for manual review

7. Show diff summary

## Source of Truth

- `pyproject.toml` / `setup.py` - Project metadata
- `.env.example` - Environment variables
- `Makefile` - Available commands
- `requirements.txt` - Dependencies

## Commands

```bash
# List Makefile targets
make help

# Show Flask commands
flask --help

# Show project info
pip show <project-name>
```

## Documentation Structure

```
docs/
├── SETUP.md           # Getting started
├── RUNBOOK.md         # Operations guide
├── API.md             # API reference
├── CODEMAPS/          # Architecture docs
└── GUIDES/            # Feature guides
```

Invokes the **doc-updater** agent.
