"""Query interface for catalog indexes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def load_classification_index(index_path: Path | str) -> Optional[dict[str, Any]]:
    """Load a classification index from file.

    Args:
        index_path: Path to file_classification.json.

    Returns:
        Index data or None if loading fails.
    """
    index_path = Path(index_path)
    if not index_path.exists():
        return None

    try:
        content = index_path.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return None


def load_dependencies_index(index_path: Path | str) -> Optional[dict[str, Any]]:
    """Load a dependencies index from file.

    Args:
        index_path: Path to module_dependencies.json.

    Returns:
        Index data or None if loading fails.
    """
    index_path = Path(index_path)
    if not index_path.exists():
        return None

    try:
        content = index_path.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return None


def query_by_category(
    index: dict[str, Any],
    category: str,
) -> list[dict[str, Any]]:
    """Query files by category.

    Args:
        index: Classification index data.
        category: Category name to filter by.

    Returns:
        List of file classifications in that category.
    """
    results = []
    files = index.get("files", {})

    for file_path, classification in files.items():
        if classification.get("primary_category") == category:
            results.append({
                "file_path": file_path,
                **classification,
            })

    return results


def query_by_file(
    index: dict[str, Any],
    file_path: str,
) -> Optional[dict[str, Any]]:
    """Query classification for a specific file.

    Args:
        index: Classification index data.
        file_path: Relative path to the file.

    Returns:
        File classification or None if not found.
    """
    files = index.get("files", {})
    classification = files.get(file_path)

    if classification:
        return {
            "file_path": file_path,
            **classification,
        }

    return None


def query_depends_on(
    index: dict[str, Any],
    file_path: str,
) -> list[str]:
    """Query files that depend on (import) a given file.

    Args:
        index: Dependencies index data.
        file_path: Relative path to the file.

    Returns:
        List of file paths that import this file.
    """
    modules = index.get("modules", {})
    module_info = modules.get(file_path)

    if module_info:
        return module_info.get("imported_by", [])

    return []


def query_imports(
    index: dict[str, Any],
    file_path: str,
) -> Optional[dict[str, Any]]:
    """Query what a file imports.

    Args:
        index: Dependencies index data.
        file_path: Relative path to the file.

    Returns:
        Dictionary with 'imports' (internal) and 'external' lists, or None.
    """
    modules = index.get("modules", {})
    module_info = modules.get(file_path)

    if module_info:
        return {
            "imports": module_info.get("imports", []),
            "external": module_info.get("external", []),
        }

    return None


def get_summary(index: dict[str, Any]) -> dict[str, Any]:
    """Get summary statistics from an index.

    Args:
        index: Classification or dependencies index data.

    Returns:
        Summary dictionary with counts and timestamp.
    """
    return {
        "file_count": index.get("file_count", index.get("module_count", 0)),
        "by_category": index.get("by_category", {}),
        "generated": index.get("generated", "unknown"),
        "schema_version": index.get("schema_version", "unknown"),
    }
