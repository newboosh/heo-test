"""Dependency tracking for Python modules."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModuleDependencies:
    """Dependency information for a single module."""

    imports: list[str] = field(default_factory=list)  # Internal modules this file imports
    imported_by: list[str] = field(default_factory=list)  # Files that import this file
    external: list[str] = field(default_factory=list)  # External packages


def _parse_python_file(file_path: Path) -> Optional[ast.AST]:
    """Parse a Python file and return its AST."""
    if file_path.suffix.lower() != ".py":
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, IOError):
        return None


def extract_imports(file_path: Path | str) -> list[str]:
    """Extract all import statements from a Python file.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of imported module names (e.g., ['os', 'app.models.user']).
    """
    file_path = Path(file_path)
    tree = _parse_python_file(file_path)

    if tree is None:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import os, sys
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            # from os import path
            # from . import utils
            # from ..models import User
            if node.module:
                # Has a module name
                if node.level > 0:
                    # Relative import with module: from .utils import x
                    prefix = "." * node.level
                    imports.append(f"{prefix}{node.module}")
                else:
                    # Absolute import
                    imports.append(node.module)
            else:
                # Relative import without module: from . import utils
                prefix = "." * node.level
                for alias in node.names:
                    if alias.name == "*":
                        imports.append(prefix)
                    else:
                        imports.append(f"{prefix}{alias.name}")

    return imports


def resolve_import(
    import_name: str,
    root_dir: Path,
    current_file: Optional[Path] = None,
) -> Optional[str]:
    """Resolve an import name to a file path.

    Args:
        import_name: The module name (e.g., 'app.models.user').
        root_dir: Project root directory.
        current_file: The file containing the import (for relative imports).

    Returns:
        Relative file path if internal module, None if external.
    """
    # Handle relative imports
    if import_name.startswith("."):
        if current_file is None:
            return None

        # Count leading dots
        level = 0
        for char in import_name:
            if char == ".":
                level += 1
            else:
                break

        # Get the actual module name after dots
        module_part = import_name[level:]

        # Start from current file's directory
        try:
            current_dir = current_file.relative_to(root_dir).parent
        except ValueError:
            current_dir = current_file.parent

        # Go up 'level' directories (level=1 means same package)
        for _ in range(level - 1):
            current_dir = current_dir.parent

        if module_part:
            # Combine with module path
            module_path = module_part.replace(".", "/")
            target_path = current_dir / module_path
        else:
            target_path = current_dir

        # Try as .py file
        py_path = root_dir / f"{target_path}.py"
        if py_path.exists():
            return str(target_path) + ".py"

        # Try as package
        init_path = root_dir / target_path / "__init__.py"
        if init_path.exists():
            return str(target_path / "__init__.py")

        return None

    # Absolute import - convert to file path
    parts = import_name.split(".")

    # Try progressively shorter paths (app.models.user -> app/models/user.py, app/models.py, etc.)
    for i in range(len(parts), 0, -1):
        module_path = "/".join(parts[:i])

        # Try as .py file
        py_path = root_dir / f"{module_path}.py"
        if py_path.exists():
            return f"{module_path}.py"

        # Try as package
        init_path = root_dir / module_path / "__init__.py"
        if init_path.exists():
            return f"{module_path}/__init__.py"

    # Not found in project - assume external
    return None


def build_dependency_graph(
    root_dir: Path | str,
    file_paths: list[str],
) -> dict[str, ModuleDependencies]:
    """Build a complete dependency graph for a set of files.

    Args:
        root_dir: Project root directory.
        file_paths: List of relative file paths to analyze.

    Returns:
        Dictionary mapping file paths to their dependencies.
    """
    root_dir = Path(root_dir)
    graph: dict[str, ModuleDependencies] = {}

    # Initialize all files in graph
    for file_path in file_paths:
        graph[file_path] = ModuleDependencies()

    # First pass: extract imports and resolve to paths
    for file_path in file_paths:
        full_path = root_dir / file_path
        if not full_path.exists() or full_path.suffix != ".py":
            continue

        imports = extract_imports(full_path)
        deps = graph[file_path]

        for import_name in imports:
            resolved = resolve_import(import_name, root_dir, full_path)

            if resolved:
                # Internal import
                if resolved not in deps.imports:
                    deps.imports.append(resolved)
            else:
                # External import - extract base package name
                base_package = import_name.lstrip(".").split(".")[0]
                if base_package and base_package not in deps.external:
                    deps.external.append(base_package)

    # Second pass: build reverse dependencies (imported_by)
    for file_path, deps in graph.items():
        for imported_file in deps.imports:
            if imported_file in graph:
                if file_path not in graph[imported_file].imported_by:
                    graph[imported_file].imported_by.append(file_path)

    return graph
