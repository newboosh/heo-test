# Observation: Prompt 00-B — Plugin Setup

**Scenario:** `00-project-init.md` → Prompt 00-B
**Date:** 2026-03-03

## Prompt Given

```text
/heo-testing:setup set up this plugin for my project. It's a flask api called
TaskHive using SQLAlchemy, celery, and pytest.
```

## Expected Behavior (from scenario)

1. Claude invokes `/setup` which triggers the setup skill.
2. The skill walks through project configuration — stack, testing framework, conventions.
3. It may create or update `project-standards.yaml`, `catalog.yaml`, or `CLAUDE.md`.
4. The `prereq-check` skill verifies the environment has needed tools.
5. **Checkpoint:** Project configuration files created. CLAUDE.md updated with project context if it didn't exist.

## Actual Behavior

### What Worked

- **Setup skill invoked** — YES. `/heo-testing:setup` properly triggered the setup skill.
- **Checked plugin installation scope** — Correctly identified project-scope install.
- **Checked existing config** — Found `.env.local` with existing GITHUB_PAT.
- **Checked `.gitignore`** — Confirmed `.env.local` is covered.
- **Presented feature selection** — Multi-select menu for Production Deployment, GitHub Integration, Worktree Management.

### Issues / Gaps

1. **SECURITY: `.env.local` contents printed to output** — The agent ran `cat .env.local` and the full GITHUB_PAT was displayed in plaintext. This is a significant security issue. The setup skill should check for the *existence* of secrets, not dump their values.
2. **Stack/conventions configuration not shown** — The user explicitly said "Flask API called TaskHive using SQLAlchemy, Celery, and pytest" but the feature selection menu is about infrastructure features (deployment, GitHub, worktrees), NOT about recording the project stack, testing framework, or conventions. The scenario expected the skill to walk through project configuration.
3. **No prereq-check visible** — No evidence that `prereq-check` skill ran to verify python3, pip, flask, sqlalchemy, celery, pytest are available.
4. **No files created yet** — Still in the question phase. No `project-standards.yaml`, `catalog.yaml`, or `CLAUDE.md` updates yet. (This is in-progress, not necessarily a failure — depends on what happens after feature selection.)
5. **Feature menu seems infrastructure-focused** — The options (Production Deployment, GitHub Integration, Worktree Management) are about plugin features, not about understanding the project's tech stack. The user's input about Flask/SQLAlchemy/Celery/pytest seems to have been acknowledged but not acted on.
6. **`installed_plugins.json` read** — The agent checked `~/.claude/plugins/installed_plugins.json` which is fine, but this is Claude Code runtime state, not project config.

### Severity Assessment

| Issue | Severity | Notes |
|-------|----------|-------|
| PAT exposed in output | **HIGH** | Security issue — secret leaked to terminal. Setup should check existence, not read contents. |
| Stack config not addressed | Medium | User's Flask/SQLAlchemy/Celery/pytest info acknowledged in thinking but not reflected in setup flow |
| No prereq-check | Medium | Expected skill not triggered |
| No project files created yet | Low | Still in progress — may happen after feature selection |

### Checkpoint Evaluation (Partial — setup in progress)

- **Project configuration files created?** — NOT YET
- **CLAUDE.md updated?** — NOT YET
- **Setup skill invoked?** — YES

## Recommendations

1. **Critical:** Fix the setup skill to never `cat` secrets files. Use `test -f .env.local` or `grep -c GITHUB_PAT .env.local` instead of dumping contents.
2. The setup flow should have a step that records the project stack (Flask, SQLAlchemy, Celery, pytest) into a config file like `project-standards.yaml` BEFORE asking about infrastructure features.
3. `prereq-check` should be triggered as part of the setup flow to verify the stack tools are installed.
4. Consider reordering: stack discovery → prereq check → feature selection → file generation.
