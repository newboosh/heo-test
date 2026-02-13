# Mutation Testing

**Purpose:** Audit test suite quality by injecting faults and checking if tests catch them.
**Python framework:** mutmut
**Key text:** *Software Testing: A Craftsman's Approach* (Jorgensen, 2013)

## How It Works

1. Parse source code into AST
2. Apply **mutation operators** (small, systematic code changes)
3. Run test suite against each mutant
4. **Killed** mutant = tests caught the fault (good)
5. **Survived** mutant = tests have a blind spot (investigate)

## Mutation Operators That Reveal Real Gaps

| Operator | Mutation | What It Catches |
|----------|----------|-----------------|
| Conditional boundary | `>` → `>=` | Off-by-one errors in tests |
| Negate conditional | `==` → `!=` | Inverted logic not tested |
| Return value | `return x` → `return None` | Missing return value assertions |
| Void method removal | `save(x)` → (deleted) | Side effects not verified |
| Arithmetic | `+` → `-` | Calculations not tested precisely |
| Constant replacement | `0` → `1` | Boundary values not checked |

**Most valuable to fix first:**
1. Conditional boundary survivors (off-by-one bugs are real production bugs)
2. Return value survivors (missing assertions)
3. Void method removal survivors (untested side effects)

## The Equivalent Mutant Problem

Some mutations produce code that behaves identically to the original:

```python
# Original
def is_positive(n):
    return n > 0

# Mutant: n >= 0  — different for n=0 (real survivor, fix it)
# Mutant: n > -1  — equivalent for integers (noise, ignore it)
```

Equivalent mutants show as "survivors" but aren't test gaps. Expect 5-15% of survivors to be equivalent. Don't chase them.

## The Runtime Problem

Mutation testing multiplies test runtime by the number of mutants:

| Module | Possible Mutants | Test Suite | Mutation Time |
|--------|-----------------|------------|---------------|
| Small (50 lines) | ~30 | 10 sec | ~5 min |
| Medium (200 lines) | ~150 | 30 sec | ~75 min |
| Large (500 lines) | ~400 | 2 min | ~13 hours |

**This is why mutation testing is an audit tool, not a CI gate.**

### Mitigation Strategies

- Run on critical modules only, not the whole codebase
- Use incremental mutation (only mutate changed lines)
- Run nightly/weekly, not on every push
- Set a timeout per mutant to kill infinite loops
- Parallelize with `--runner=pytest` and `pytest-xdist`

## Decision: When To Run

```
Is this code on a critical path?
├── Yes (payments, auth, data integrity, calculations)
│   ├── Is coverage already >80%?
│   │   ├── Yes → Run mutation testing to find assertion gaps
│   │   └── No → Write more tests first, then mutate
│   └── Is the code stable (not changing weekly)?
│       ├── Yes → Schedule periodic mutation audit
│       └── No → Wait until it stabilizes
└── No (CRUD, config, glue, UI)
    └── Skip mutation testing (low ROI)
```

## Interpreting Results

| Mutation Score | Interpretation | Action |
|---------------|----------------|--------|
| **>80%** | Strong test suite | Fix critical survivors only |
| **60-80%** | Decent, assertion gaps exist | Add targeted assertions |
| **40-60%** | Significant blind spots | Major test improvement needed |
| **<40%** | Tests are decorative | Rewrite tests with TDD |

## Usage in This Project (mutmut)

```bash
# Run on a specific module
mutmut run --paths-to-mutate=app/services/payment_service.py

# View results summary
mutmut results

# Inspect a specific survivor (by ID)
mutmut show 42

# Generate HTML report
mutmut html

# Apply a surviving mutant to see what was changed
mutmut apply 42
# Then run tests to understand why they didn't catch it
pytest tests/ -v
# Revert
mutmut apply 42 --revert
```

## Workflow: Mutation Audit

1. **Select target:** Pick a critical module (payment, auth, data integrity)
2. **Check baseline:** Ensure existing tests pass and coverage is >80%
3. **Run mutation:** `mutmut run --paths-to-mutate=<module>`
4. **Triage survivors:** Sort by operator type, focus on conditional and return-value mutations
5. **Fix top 5-10:** Write tests that kill the most important survivors
6. **Accept the rest:** ~85% kill rate is a healthy target. Don't chase 100%.
7. **Document:** Note which modules have been audited and when
