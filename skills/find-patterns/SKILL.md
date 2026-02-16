---
name: find-patterns
description: Find similar implementations, patterns, and prior art in the codebase. Used by Context Agent and QA Agent.
---

# Find Patterns

Locate similar implementations to use as reference or for consistency checking.

## Input

- **description**: What kind of code to find (e.g., "API endpoint", "service class", "pytest fixture")
- **scope**: Optional directory to search within

## Process

1. **Identify search terms** from the description
   - Feature type (endpoint, service, model, test)
   - Technology (Flask, SQLAlchemy, pytest)
   - Pattern name (repository, factory, decorator)

2. **Search by file naming conventions**
   ```
   Glob: "**/*service*.py"
   Glob: "**/*repository*.py"
   Glob: "**/test_*.py"
   ```

3. **Search by code patterns**
   ```
   Grep: "@bp.route"          # Flask endpoints
   Grep: "class.*Service"     # Service classes
   Grep: "@pytest.fixture"    # Test fixtures
   Grep: "def test_"          # Test functions
   ```

4. **Rank by relevance**
   - Exact pattern match > partial match
   - Recent files > old files
   - Same directory > different directory

## Output

```markdown
## Similar Implementations Found

### Best Match
- **File:** `app/services/user_service.py`
- **Relevance:** Same pattern (service class), same domain
- **Key sections:** Lines 15-45 (main implementation)

### Other Examples
- `app/services/market_service.py` - Similar service pattern
- `app/services/payment_service.py` - Shows error handling
```

## Empty State Handling

**If no patterns found:**
```markdown
## Similar Implementations Found

### Status
No similar implementations found for: [description]

### Recommendations
- This may be a new pattern for this codebase
- Check external documentation for reference implementations
- Consider whether existing patterns can be adapted
- Document this as the reference implementation for future use
```

## Skill Dependencies

```
find-patterns (this skill)
    ↑
    ├── context-agent (finds examples before work)
    └── qa-agent (checks consistency after work)
```

This skill is a **leaf dependency** - it does not invoke other skills.

## Usage

**Context Agent:** Find examples before work begins
**QA Agent:** Find patterns to check consistency against
