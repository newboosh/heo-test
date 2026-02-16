# Agent Orchestration

## Available Agents

Located in `agents/`:

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| tdd-guide | Test-driven development | New features, bug fixes |
| code-reviewer | Code review | After writing code |
| security-reviewer | Security analysis | Before commits |
| build-error-resolver | Fix build errors | When build fails |
| e2e-runner | E2E testing | Critical user flows |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| doc-updater | Documentation | Updating docs |
| git-orchestrator | Git operations automation | Task boundaries, checkpoints |
| librarian | Doc organization & file audits | Stale docs, broken references |

## Immediate Agent Usage

Use agents proactively without waiting for user prompt:

| Trigger | Agent to Use |
|---------|--------------|
| Complex feature request | **planner** agent |
| Code just written/modified | **code-reviewer** agent |
| Bug fix or new feature | **tdd-guide** agent |
| Architectural decision needed | **architect** agent |
| Security-sensitive code | **security-reviewer** agent |
| Build failure | **build-error-resolver** agent |
| Task boundary / checkpoint | **git-orchestrator** agent |
| Stale/broken doc references | **librarian** agent |

## Parallel Task Execution

**ALWAYS** use parallel Task execution for independent operations:

```markdown
# GOOD: Parallel execution (single message, multiple Task calls)
Launch 3 agents simultaneously:
1. Agent 1: Security analysis of auth.py
2. Agent 2: Performance review of cache.py
3. Agent 3: Type checking of utils.py

# BAD: Sequential when unnecessary
First agent 1, then wait, then agent 2, then wait, then agent 3
```

### Example: Parallel Code Review

```python
# Launch multiple reviews in parallel
Task(
    subagent_type="general-purpose",
    prompt="Review auth.py for security issues"
)
Task(
    subagent_type="general-purpose",
    prompt="Review api.py for performance issues"
)
Task(
    subagent_type="general-purpose",
    prompt="Check models.py for SQL injection risks"
)
```

## Multi-Perspective Analysis

For complex problems, use split role sub-agents to get diverse viewpoints:

| Role | Focus |
|------|-------|
| Factual reviewer | Verify correctness of claims and implementation |
| Senior engineer | Code quality, maintainability, best practices |
| Security expert | Vulnerabilities, attack vectors, data exposure |
| Consistency reviewer | API consistency, naming conventions, patterns |
| Redundancy checker | Dead code, duplicate logic, unnecessary complexity |

### Example: Architecture Review

```markdown
For this architecture decision, get perspectives from:

1. **Senior Engineer**: Is this maintainable? Scalable?
2. **Security Expert**: What are the attack vectors?
3. **Performance Expert**: What are the bottlenecks?
4. **Junior Developer**: Is this understandable?
```

## Agent Selection Guide

### By Task Type

| Task | Primary Agent | Supporting Agent |
|------|---------------|------------------|
| New feature | planner → tdd-guide | code-reviewer |
| Bug fix | tdd-guide | code-reviewer |
| Refactoring | refactor-cleaner | code-reviewer |
| Security audit | security-reviewer | - |
| Performance issue | architect | - |
| Documentation | doc-updater | librarian |
| E2E tests | e2e-runner | tdd-guide |
| Version control ops | git-orchestrator | - |
| Doc audits / link fixes | librarian | doc-updater |

### By Complexity

| Complexity | Approach |
|------------|----------|
| Simple (1 file) | Direct implementation, then code-reviewer |
| Medium (2-5 files) | planner first, then implement |
| Complex (6+ files) | architect → planner → implement in phases |

## Agent Chaining

For complex tasks, chain agents in sequence:

```markdown
1. **architect**: Design the overall approach
2. **planner**: Break down into implementable tasks
3. **tdd-guide**: Implement each task with tests
4. **code-reviewer**: Review completed implementation
5. **security-reviewer**: Final security check
6. **git-orchestrator**: Checkpoint and commit changes
```

## Best Practices

1. **Use agents proactively** - Don't wait for problems
2. **Parallelize independent work** - Save time
3. **Trust agent output** - They're specialized
4. **Chain for complex tasks** - Multiple perspectives
5. **Review before commit** - Always use code-reviewer
