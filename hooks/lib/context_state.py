#!/usr/bin/env python3
"""
Context pressure state management library.

Provides atomic JSON read/write for hook-state.json and hook-config.json
with defaults and corruption recovery. Used by context-pressure.py hook
and context-monitor agent.

Files managed:
  .context/hook-state.json   - Hook writes, agent reads (pressure tracking)
  .context/hook-config.json  - Agent writes, hook reads (thresholds/weights)
  .context/agent-log.json    - Agent writes and reads (checkpoint/tuning log)
"""

import copy
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# State file written by hook, read by agent
DEFAULT_STATE: Dict[str, Any] = {
    "version": 1,
    "session_id": "",
    "total_calls": 0,
    "pressure_score": 0,
    "pressure_since_checkpoint": 0,
    "last_checkpoint_at_call": 0,
    "tool_counts": {},
    "streak": {"tool": "", "count": 0},
    "files_read": {},
    "re_reads": [],
    "flags": {
        "checkpoint_requested": False,
        "streak_warning_sent": False,
        "re_read_warning_sent": False,
    },
    "last_updated": "",
}

# Config file written by agent, read by hook
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "pressure_threshold": 8,
    "streak_limit": 3,
    "re_read_gap": 5,
    "weights": {
        "Read": 3,
        "Grep": 2,
        "Bash": 2,
        "Task": 2,
        "Edit": 1,
        "Write": 1,
        "Glob": 1,
    },
    "messages": {
        "checkpoint": (
            "\n[context] Pressure {score}/{threshold}. "
            "Checkpoint: message context-monitor with findings summary.\n"
        ),
        "re_read": (
            "\n[context] Re-read: {file} (gap: {gap}). "
            "Context loss likely. Message context-monitor for recall.\n"
        ),
        "streak": (
            "\n[context] {count}x {tool} streak. "
            "Consider Task agent for batch work.\n"
        ),
    },
    "acknowledge_checkpoint": False,
    "suppress_until_call": 0,
    "disabled": False,
}

# Agent log file written and read by agent
DEFAULT_AGENT_LOG: Dict[str, Any] = {
    "version": 1,
    "checkpoints": [],
    "tuning_history": [],
}

# File names within .context/
STATE_FILE = "hook-state.json"
CONFIG_FILE = "hook-config.json"
AGENT_LOG_FILE = "agent-log.json"


def ensure_context_dir(cwd: str) -> Path:
    """Create .context/ directory if it doesn't exist.

    Args:
        cwd: Project working directory.

    Returns:
        Path to the .context/ directory.
    """
    context_dir = Path(cwd) / ".context"
    context_dir.mkdir(parents=True, exist_ok=True)
    return context_dir


def _atomic_write(filepath: Path, data: Dict[str, Any]) -> None:
    """Write JSON atomically using tempfile + rename.

    Writes to a temporary file in the same directory, then renames
    to avoid partial reads from concurrent processes.

    Args:
        filepath: Target file path.
        data: Dictionary to serialize as JSON.
    """
    parent = filepath.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, str(filepath))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _safe_read(filepath: Path, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Read JSON with corruption recovery.

    Returns defaults if:
    - File doesn't exist
    - File is empty
    - File contains invalid JSON
    - Any I/O error occurs

    Args:
        filepath: Path to JSON file.
        defaults: Default dict to return on any failure.

    Returns:
        Parsed JSON dict, or deep copy of defaults.
    """
    if not filepath.exists():
        return copy.deepcopy(defaults)

    try:
        content = filepath.read_text(encoding="utf-8")
        if not content.strip():
            return json.loads(json.dumps(defaults))
        data = json.loads(content)
        if not isinstance(data, dict):
            return json.loads(json.dumps(defaults))
        return data
    except (json.JSONDecodeError, IOError, OSError):
        return json.loads(json.dumps(defaults))


def load_state(context_dir: Path) -> Dict[str, Any]:
    """Load hook-state.json with defaults on missing/corrupt.

    Args:
        context_dir: Path to .context/ directory.

    Returns:
        State dict (may be defaults if file missing/corrupt).
    """
    return _safe_read(context_dir / STATE_FILE, DEFAULT_STATE)


def save_state(context_dir: Path, state: Dict[str, Any]) -> None:
    """Save hook-state.json atomically.

    Args:
        context_dir: Path to .context/ directory.
        state: State dict to write.
    """
    state["last_updated"] = datetime.now().isoformat(timespec="seconds")
    _atomic_write(context_dir / STATE_FILE, state)


def load_config(context_dir: Path) -> Dict[str, Any]:
    """Load hook-config.json with defaults on missing/corrupt.

    Args:
        context_dir: Path to .context/ directory.

    Returns:
        Config dict (may be defaults if file missing/corrupt).
    """
    config = _safe_read(context_dir / CONFIG_FILE, DEFAULT_CONFIG)
    # Ensure all default keys exist (forward-compat for new fields)
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict) and isinstance(config[key], dict):
            # Merge nested defaults (e.g., new tool weight added)
            for sub_key, sub_value in value.items():
                if sub_key not in config[key]:
                    config[key][sub_key] = sub_value
    return config


def save_config(context_dir: Path, config: Dict[str, Any]) -> None:
    """Save hook-config.json atomically.

    Args:
        context_dir: Path to .context/ directory.
        config: Config dict to write.
    """
    _atomic_write(context_dir / CONFIG_FILE, config)


def load_agent_log(context_dir: Path) -> Dict[str, Any]:
    """Load agent-log.json with defaults on missing/corrupt.

    Args:
        context_dir: Path to .context/ directory.

    Returns:
        Agent log dict.
    """
    return _safe_read(context_dir / AGENT_LOG_FILE, DEFAULT_AGENT_LOG)


def save_agent_log(context_dir: Path, log: Dict[str, Any]) -> None:
    """Save agent-log.json atomically.

    Args:
        context_dir: Path to .context/ directory.
        log: Agent log dict to write.
    """
    _atomic_write(context_dir / AGENT_LOG_FILE, log)
