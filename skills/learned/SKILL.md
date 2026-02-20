---
name: learned
description: Store and retrieve reusable patterns learned across sessions
model: sonnet
agent_only: true
---

# Learned Patterns

This skill manages the storage and retrieval of reusable patterns extracted from development sessions via the `/learn` command.

## How It Works

1. During a session, the `/learn` command extracts patterns worth preserving
2. Patterns are saved as markdown files in this directory
3. Future sessions can reference these patterns for consistency

## Directory Structure

Pattern files are created dynamically by the `/learn` command. Each file captures a specific pattern, convention, or insight discovered during development.
