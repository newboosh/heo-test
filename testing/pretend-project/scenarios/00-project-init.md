# Scenario 00: Project Initialization

## Features Exercised

- Commands: `/help`, `/setup`, `/catalog init`
- Skills: setup, prereq-check, project-skeleton, catalog
- Hooks: session-validate-tools (auto), session-ensure-git-hooks (auto),
  session-guard-init (auto), capture-query (auto)

## Prerequisites

None. This is the first scenario.

## Setup

Start from the bare scaffold committed to a fresh git repo. Launch Claude
with the heo-test plugin installed.

## Prompts

### Prompt 00-A: Orientation

```text
What commands does this plugin give me? I have a new Flask project and want
to understand what tools are available before I start building.
```

**What Should Happen:**
- Claude runs `/help` (or the help skill) and lists available commands
  grouped by category.
- The session-validate-tools hook fires on session start and checks for
  python3, pip, git, ruff, mypy, pytest.
- The session-ensure-git-hooks hook fires and sets up pre-commit hooks.
- The capture-query hook captures this prompt for session recap.

**Checkpoint:** Help output is displayed. No tool validation errors (assuming
the dev tools are installed). Git hooks exist in `.git/hooks/`.

---

### Prompt 00-B: Plugin Setup

```text
Set up this plugin for my project. It's a Flask API called TaskHive using
SQLAlchemy, Celery, and pytest.
```

**What Should Happen:**
- Claude invokes `/setup` which triggers the setup skill.
- The skill walks through project configuration — stack, testing framework,
  conventions.
- It may create or update project-standards.yaml, catalog.yaml, or
  CLAUDE.md.
- The prereq-check skill verifies the environment has needed tools.

**Checkpoint:** Project configuration files created. CLAUDE.md updated with
project context if it didn't exist.

---

### Prompt 00-C: Build File Catalog

```text
Build a file catalog for this project so you can quickly navigate it later.
```

**What Should Happen:**
- Claude invokes `/catalog init` which triggers the catalog skill.
- It scans the project structure and classifies files by role (model, route,
  service, test, config, docs).
- Creates or updates catalog.yaml.

**Checkpoint:** catalog.yaml exists with entries for all scaffold files. Each
file has a classification.
