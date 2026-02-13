# Sprint Skill

Entry point for the automated 13-phase sprint lifecycle. See `docs/SPRINT_LIFECYCLE.md` for full reference.

## Quick Start

```text
/sprint Add user authentication    # Start a new sprint
/sprint                            # Smart router (show state, offer choices)
/sprint status                     # Quick status check
/sprint reset                      # Clear sprint state
```

## Testing

### Automated Tests

```bash
python3 -m pytest scripts/sprint/tests/test_validate.py -v
```

57 tests covering: envelope validation, phase 1-13 body validation, directory validation, sprint meta, rollback.

### Template Validation

```bash
python3 -c "
from scripts.sprint.validate import load_phase_output
from pathlib import Path
for f in sorted(Path('skills/sprint/templates').glob('*.yaml')):
    env = load_phase_output(f)
    print(f'OK: {f.name} (phase {env.phase})')
"
```

### Manual Testing

```bash
/sprint Add user authentication     # Walk through phases 1-5
ls -la .sprint/                     # Check outputs
python3 -m scripts.sprint.validate .sprint/   # Validate all files
/sprint                             # Test smart router
/sprint reset                       # Clean up
```

## Modifying

| What to change | Where |
|---|---|
| Workflow logic | `SKILL.md` |
| Phase schemas | `templates/*.yaml` |
| Validation rules | `scripts/sprint/validate.py` |
| Tests | `scripts/sprint/tests/test_validate.py` |
| Architecture decisions | `docs/planning/TECHNICAL_DECISIONS.md` (Decisions 5-9) |
| Lifecycle reference | `docs/SPRINT_LIFECYCLE.md` |

After changes:
1. Update templates if schema changed
2. Update validate.py if adding/changing rules
3. Run tests: `python3 -m pytest scripts/sprint/tests/ -v`
4. Validate templates pass through the validator
