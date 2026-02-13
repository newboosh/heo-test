# Heo-Test

A Claude Code testing plugin for the heo project.

## Installation

### Via Claude Code

```bash
/plugin add newboosh/heo-test
```

### Manual

```bash
git clone git@github.com:newboosh/heo-test.git .claude
```

## Configuration

1. Copy `.env.example` to `.env.local`
2. Fill in the values for features you want to use

## Directory Structure

```
├── agents/           # Specialized AI agents
├── commands/         # Slash commands
├── hooks/            # Lifecycle hooks
├── rules/            # Project standards and guidelines
├── scripts/          # Shell scripts for automation
└── skills/           # Reusable skill modules
```

## License

MIT
