# Heo

A comprehensive Claude Code plugin for Python/Flask development with worktree management, TDD workflow, code review, and production deployment scripts.

## Features

- **Git Worktree Management** (`/tree`) - Manage parallel development branches
- **Test-Driven Development** (`/tdd`) - Enforced TDD workflow with pytest
- **Code Review** (`/code-review`) - Automated code quality checks
- **Security Review** (`/verify`) - Security analysis before commits
- **Build Error Resolution** (`/build-fix`) - Systematic build error fixing
- **Production Deployment** (`/deploy`) - SSH-based deployment scripts
- **Documentation Updates** (`/update-docs`) - Keep docs in sync with code

## Installation

> **Full walkthrough with key transfer instructions:** [docs/INSTALL_GUIDE.md](docs/INSTALL_GUIDE.md)

### Quick Install (Recommended)

```bash
# If you already have the repo cloned:
bash scripts/install-plugin.sh --key /path/to/deploy_heo

# Or download and run directly:
curl -sO https://raw.githubusercontent.com/FrostyTeeth/claude_plugin_source/main/scripts/install-plugin.sh
bash install-plugin.sh --key /path/to/deploy_heo
```

### Shell Aliases

After install, add to your `~/.zshrc` or `~/.bashrc`:

```bash
source ~/.heo-plugin/scripts/shell-alias.sh
```

Then use:
- `claude-heo` or `ch` — launch Claude with the plugin
- `claude-heo-tree` or `cht` — launch in a worktree with task context

### Other Install Methods

```bash
# With GitHub PAT instead of deploy key
bash scripts/install-plugin.sh --pat ghp_xxxxxxxxxxxx

# Manual clone (requires SSH config — see INSTALL_GUIDE.md)
git clone git@heo.github.com:newboosh/heo.git ~/.heo-plugin
claude --add-dir ~/.heo-plugin
```

## Configuration

### Quick Setup

Run `/setup` to interactively configure the plugin for your project.

### Manual Setup

Most features work out of the box. Some features (deployment, GitHub integration) require environment variables — create a `.env.local` in your project root if needed.

| Feature | Required Variables |
|---------|-------------------|
| Production Deployment | `PRODUCTION_DOMAIN`, `PRODUCTION_SERVER_IP` |
| GitHub Integration | `REPO_ORIGIN_URL`, `REPO_ORIGIN_PAT` |
| Worktree Management | None (works out of the box) |

## Directory Structure

```
├── agents/           # Specialized AI agents
├── commands/         # Slash commands (/tree, /tdd, etc.)
├── contexts/         # Context presets (dev, review, research)
├── hooks/            # Git safety and auto-formatting hooks
├── rules/            # Project standards and guidelines
├── scripts/          # Shell scripts for automation
├── skills/           # Reusable skill modules
├── standards/        # Coding standards (conventional commits, etc.)
└── templates/        # Document and workflow templates
```

## Hooks

The plugin includes automatic hooks that run during Claude Code sessions:

| Hook | Trigger | Action |
|------|---------|--------|
| **Git Safety** | Any `git` command | Blocks `--no-verify`, direct push to main, `reset --hard` |
| **Python Formatter** | Edit `.py` files | Auto-formats with ruff, warns about `print()` |
| **Template Security** | Edit `.html` files | Warns about `\|safe` filter and missing CSP nonce |
| **Session Validation** | Session start | Checks for required dev tools |

Hooks run directly from the plugin directory using `${CLAUDE_PLUGIN_ROOT}`. Project-specific hooks (if any) run in parallel and are not modified.

### Upgrading from v2.0.x

If you used an earlier version that synced hooks to projects, you may have orphaned files. To clean up:

```bash
# Remove synced hook files (safe to run even if they don't exist)
rm -rf .claude/hooks/pre-git-safety-check.py \
       .claude/hooks/post-python-format.py \
       .claude/hooks/session-validate-tools.py \
       .claude/hooks/session-ensure-git-hooks.py \
       .claude/hooks/lib/

# Remove [heo] hooks from .claude/settings.json if present
# (Only needed if you have custom hooks you want to keep)
```

The plugin no longer modifies project files - hooks run from the plugin directory.

## Stack

Designed for:
- Python 3.9+
- Flask
- SQLAlchemy
- Celery
- pytest

## Credits

This project builds upon and is inspired by several sources:

- **Base Implementation**: Most of the foundational work is based on [everything-claude-code](https://github.com/affaan-m/everything-claude-code) by affaan-m
- **Librarian Workflow**: Agent, skill, and command implementation by Steve Glen
- **Dignified Python Principles**: Inspired by the [10 Rules for Dignified Python](https://dagster.io/blog/dignified-python-10-rules-to-improve-your-llm-agents) by the Dagster team

## License

MIT