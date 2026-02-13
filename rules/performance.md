# Performance Optimization

## Model Selection Strategy

### Haiku (Fast, Cost-Effective)
**90% of Sonnet capability, 3x cost savings**

Use for:
- [placeholder]

### Sonnet (Best Coding Model)
**Recommended for most development work**

Use for:
- Main development work
- Lightweight agents with frequent invocation
- Pair programming and code generation
- Worker agents in multi-agent systems
- Quick code reviews
- Simple refactoring tasks

### Opus (Deepest Reasoning)
**Maximum capability, use strategically**

Use for:
- Complex architectural decisions
- Maximum reasoning requirements
- Research and analysis tasks
- Difficult debugging sessions
- System design review
- Orchestrating multi-agent workflows
- Complex coding tasks
- Debugging intricate issues
- API design and implementation

## Context Window Management

### High Context Sensitivity Tasks
Avoid these when in the last 20% of context window:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions
- Multi-file code reviews

### Lower Context Sensitivity Tasks
Safe to perform with limited context:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes
- Configuration changes

### When Context is Running Low

1. **Summarize** current progress
2. **Commit** completed work
3. **Start fresh session** with clear context
4. **Use `/compact`** to summarize conversation

## Ultrathink + Plan Mode

For complex tasks requiring deep reasoning:

1. **Enable Plan Mode** for structured approach
2. Use `ultrathink` for enhanced thinking time
3. "Rev the engine" with multiple critique rounds
4. Use split role sub-agents for diverse analysis:
   - Factual reviewer
   - Senior engineer perspective
   - Security expert view
   - Consistency checker

## Parallel Execution

### Always Parallelize Independent Operations

```markdown
# GOOD: Parallel execution
Launch 3 agents simultaneously:
1. Agent 1: Security analysis of auth module
2. Agent 2: Performance review of cache system
3. Agent 3: Type checking of utils module

# BAD: Sequential when unnecessary
First agent 1... wait... then agent 2... wait... then agent 3
```

### Use Task Tool for Parallel Work

```python
# Multiple independent searches - run in parallel
Task(subagent_type="Explore", prompt="Find all API endpoints")
Task(subagent_type="Explore", prompt="Find all database models")
Task(subagent_type="Explore", prompt="Find all test files")
```

## Build Troubleshooting

If build fails:

1. **Use build-error-resolver agent** for systematic debugging
2. **Analyze error messages** carefully
3. **Fix incrementally** - one error at a time
4. **Verify after each fix** before moving to next
5. **Don't guess** - understand the root cause

## Database Query Optimization

### Common Issues

```python
# BAD: N+1 query problem
users = User.query.all()
for user in users:
    print(user.posts)  # Separate query for each user!

# GOOD: Eager loading
users = User.query.options(joinedload(User.posts)).all()
for user in users:
    print(user.posts)  # No additional queries
```

### Index Your Queries

```python
# If you frequently query by email
class User(db.Model):
    email = db.Column(db.String(120), index=True)  # Add index
```

## Caching Strategy

### Use Redis for Expensive Operations

```python
from functools import cache
import redis

r = redis.Redis()

def get_expensive_data(key: str) -> dict:
    # Check cache first
    cached = r.get(f"data:{key}")
    if cached:
        return json.loads(cached)

    # Compute if not cached
    result = expensive_computation(key)

    # Cache for 1 hour
    r.setex(f"data:{key}", 3600, json.dumps(result))
    return result
```

## Memory Management

### For Large Data Processing

```python
# BAD: Load everything into memory
data = list(huge_query.all())
process(data)

# GOOD: Process in chunks
for chunk in huge_query.yield_per(1000):
    process(chunk)
```

## Monitoring Performance

```bash
# Profile Python code
python -m cProfile -s cumtime app.py

# Memory profiling
pip install memory_profiler
python -m memory_profiler script.py
```
