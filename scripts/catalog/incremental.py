"""Incremental build support for the catalog system."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class CatalogState:
    """Persisted state for incremental builds."""

    file_hashes: dict[str, str] = field(default_factory=dict)  # path -> SHA-256
    last_build: Optional[str] = None  # ISO timestamp


def compute_file_hash(file_path: Path | str) -> Optional[str]:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        Hex string of SHA-256 hash, or None if file cannot be read.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks for memory efficiency on large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError):
        return None


def load_state(state_path: Path | str) -> CatalogState:
    """Load catalog state from file.

    Args:
        state_path: Path to .catalog_state.json.

    Returns:
        CatalogState, empty if file doesn't exist or is corrupted.
    """
    state_path = Path(state_path)

    if not state_path.exists():
        return CatalogState()

    try:
        content = state_path.read_text(encoding="utf-8")
        data = json.loads(content)
        return CatalogState(
            file_hashes=data.get("file_hashes", {}),
            last_build=data.get("last_build"),
        )
    except (json.JSONDecodeError, IOError):
        return CatalogState()


def save_state(state: CatalogState, state_path: Path | str) -> None:
    """Save catalog state to file.

    Args:
        state: CatalogState to save.
        state_path: Path to .catalog_state.json.
    """
    state_path = Path(state_path)

    data = {
        "file_hashes": state.file_hashes,
        "last_build": state.last_build,
    }

    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_changed_files(
    root_dir: Path,
    file_paths: list[str],
    state: CatalogState,
) -> list[str]:
    """Determine which files have changed since last build.

    Args:
        root_dir: Project root directory.
        file_paths: List of relative file paths to check.
        state: Previous build state.

    Returns:
        List of relative paths that have changed (new, modified, or not in state).
    """
    changed = []

    for file_path in file_paths:
        full_path = root_dir / file_path
        current_hash = compute_file_hash(full_path)

        if current_hash is None:
            # File doesn't exist or can't be read - skip
            continue

        previous_hash = state.file_hashes.get(file_path)

        if previous_hash is None or previous_hash != current_hash:
            changed.append(file_path)

    return changed


def update_state_hashes(
    root_dir: Path,
    file_paths: list[str],
    state: CatalogState,
) -> None:
    """Update state with current file hashes.

    Args:
        root_dir: Project root directory.
        file_paths: List of relative file paths to update.
        state: State to update (modified in place).
    """
    for file_path in file_paths:
        full_path = root_dir / file_path
        file_hash = compute_file_hash(full_path)
        if file_hash:
            state.file_hashes[file_path] = file_hash

    state.last_build = datetime.now(timezone.utc).isoformat()
