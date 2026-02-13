#!/usr/bin/env python3
"""Configuration constants for CodeRabbit loop system."""

from __future__ import annotations

import json
import os
from pathlib import Path

# Loop behavior
MAX_ITERATIONS = 8
POLL_INTERVAL_SECONDS = 30
CODERABBIT_WAIT_MINUTES = 5

# Rate limiting
RATE_LIMIT_THRESHOLD = 500
RATE_LIMIT_PAUSE_MINUTES = 15

# Tracker settings
TRACKER_FILE = ".coderabbit-tracker.json"
ANALYSIS_INTERVAL = 12  # PRs between pattern analysis
MAX_STORED_COMMENTS = 500

# Branch tracking
BRANCH_TRACKER_FILE = ".coderabbit-branches.json"

# Merge conflict resolution
CONFLICT_STRATEGY = "current_priority"  # "current_priority", "include_both", "manual"
CONFLICT_AUTO_RESOLVE_FILES = [
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
]

# CodeRabbit bot identifiers
CODERABBIT_USERS = ["coderabbitai", "coderabbit"]


def load_config_overrides() -> dict:
    """Load config overrides from .coderabbit-config.json if present."""
    config_paths = [
        Path.cwd() / ".coderabbit-config.json",
        Path.home() / ".config" / "coderabbit" / "config.json",
    ]

    for path in config_paths:
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

    return {}


def get_config(key: str, default=None):
    """Get a config value, checking overrides first."""
    overrides = load_config_overrides()
    if key in overrides:
        return overrides[key]

    # Check environment variable
    env_key = f"CODERABBIT_{key.upper()}"
    if env_key in os.environ:
        value = os.environ[env_key]
        # Try to parse as JSON for complex types
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    # Return module-level default
    return globals().get(key, default)
