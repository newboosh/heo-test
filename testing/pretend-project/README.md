# TaskHive — Pretend Project for heo-test Plugin Testing

## What This Is

TaskHive is a fictional collaborative task management API. It does not need to
actually run. It exists solely as a realistic testing vehicle for exercising
every feature in the heo-test Claude Code plugin.

The project is structured as:

1. **scaffold/** — A minimal but realistic Flask/SQLAlchemy/Celery project.
   Copy this into a fresh git repo to create the test environment.
2. **scenarios/** — Numbered prose prompts. Each scenario is a task you would
   give to Claude (with heo-test installed) inside the scaffolded project.
   Together they exercise every command, skill, agent, and hook in the plugin.
3. **COVERAGE.md** — A matrix mapping every heo-test feature to the scenario
   that exercises it.

## How to Use

### Setup

```bash
# 1. Create a fresh repo
mkdir ~/taskhive && cd ~/taskhive && git init

# 2. Copy the scaffold
cp -r <this-dir>/scaffold/* .
cp -r <this-dir>/scaffold/.env.example .

# 3. Create a venv and install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 4. Initial commit
git add -A && git commit -m "Initial scaffold"

# 5. Launch Claude with heo-test
claude --plugin github:newboosh/heo-test
```

### Running Scenarios

Open each scenario file in order (00 through 13). Each contains:

- **Features Exercised** — Which commands/skills/agents/hooks are tested.
- **Prerequisites** — Which scenarios must be completed first.
- **Prompt** — The exact text to give Claude. Copy-paste it.
- **What Should Happen** — Observable behaviors to verify.
- **Checkpoint** — How to confirm the feature worked.

Some scenarios branch into sub-prompts for thorough coverage.

### Principles

- Scenarios are ordered but not all are strictly sequential. The COVERAGE
  matrix notes which can run independently.
- The scaffold intentionally includes some rough edges (missing tests, a
  subtle auth bug, incomplete docs) so that quality/security/bug features
  have real material to work with.
- Hook behavior is verified passively — hooks fire automatically, so
  scenarios note what output to watch for rather than giving explicit prompts.

## Project: TaskHive

A REST API for collaborative task management.

- **Stack**: Python 3.11, Flask, SQLAlchemy, Celery, Redis, pytest
- **Features**: User auth (JWT), workspaces, tasks, assignments, comments,
  real-time notifications, background jobs, rate limiting
- **Architecture**: Layered (routes → services → models), factory pattern app
