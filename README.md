# Heo-Test

A comprehensive Claude Code testing plugin with worktree management, TDD workflow, code review, security review, and deployment scripts.

## Installation

### As a plugin directory

Clone into your project and add it to Claude Code:

```bash
git clone https://github.com/newboosh/heo-test.git /path/to/heo-test
claude --add-dir /path/to/heo-test
```

### As a marketplace source

Add the marketplace in Claude Code's plugin settings, then install plugins from it.

## Configuration

1. Copy `.env.example` to `.env.local` in your project root
2. Fill in the values for features you want to use

```bash
cp .env.example .env.local
```

### Configuration Options

| Feature | Required Variables |
|---------|-------------------|
| GitHub Integration | `REPO_ORIGIN_URL`, `REPO_ORIGIN_PAT` |
| Production Deployment | `PRODUCTION_DOMAIN`, `PRODUCTION_SERVER_IP` |
| Worktree Management | None (works out of the box) |

See `.env.example` for all available options with descriptions.

## Contents

### Commands (35)

Slash commands for common workflows: `/tree`, `/tdd`, `/code-review`, `/verify`, `/build-fix`, `/deploy`, and more.

### Agents (14)

Specialized AI agents: architect, code-reviewer, librarian, planner, qa-agent, security-reviewer, sentinel, and more.

### Skills (40)

Reusable skill modules for composition patterns, backend patterns, bug investigation, catalog management, and more.

### Rules (8)

Project standards for agents, file organization, git safety, hooks, security, performance, and testing.

### Scripts

Automation for GitHub auth, worktree management, catalog indexing, sprint tracking, and deployment.

### Hooks

Git and Claude lifecycle hooks for safety checks, formatting, and session validation.

## Directory Structure

```
├── agents/           # Specialized AI agents
├── commands/         # Slash commands
├── hooks/            # Lifecycle hooks
├── rules/            # Project standards and guidelines
├── scaffolds/        # Code generation templates
├── scripts/          # Shell scripts for automation
├── skills/           # Reusable skill modules
├── standards/        # Coding standards
├── templates/        # Document and workflow templates
└── workflows/        # Git workflow configurations
```

## License

MIT
