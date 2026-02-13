"""Dependency graph component for import analysis.

Extracts imports from Python files and builds forward/reverse dependency graphs.
Handles circular imports without infinite loops.
"""

import ast
from typing import Dict, List, Set, Optional
from pathlib import Path
from collections import defaultdict

from scripts.intelligence.utils import ast_utils, file_utils


class DependencyGraph:
    """Build and manage dependency graphs from imports."""

    def __init__(self):
        """Initialize empty dependency graph."""
        self.forward_deps: Dict[str, Set[str]] = defaultdict(set)  # file -> imports
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)  # import -> importers

    def extract_imports(self, file_path: str) -> Dict[str, List[str]]:
        """Extract imports from Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            Dict with 'internal' and 'external' import lists.
        """
        tree = ast_utils.parse_python_file(file_path)
        if not tree:
            return {"internal": [], "external": []}

        imports = {"internal": [], "external": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports["external"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full = f"{module}.{alias.name}" if module else alias.name
                    # Simple heuristic: internal if starts with . or known local patterns
                    if module and (module.startswith('.') or not '.' in module):
                        imports["internal"].append(full)
                    else:
                        imports["external"].append(full)

        return imports

    def build_graph(self, root_dir: str) -> Dict[str, Dict]:
        """Build dependency graph for directory.

        Args:
            root_dir: Root directory to analyze.

        Returns:
            Dict mapping files to their dependencies.
        """
        self.forward_deps.clear()
        self.reverse_deps.clear()

        # First pass: extract all imports
        file_imports = {}
        for python_file in file_utils.get_python_files(root_dir):
            imports = self.extract_imports(python_file)
            file_imports[python_file] = imports

        # Second pass: build forward graph
        for file_path, imports in file_imports.items():
            relative = file_utils.get_relative_path(file_path, root_dir)
            self.forward_deps[relative] = set(imports.get("internal", []))

        # Third pass: build reverse graph
        for file_path, imports in file_imports.items():
            relative = file_utils.get_relative_path(file_path, root_dir)
            for imp in imports.get("internal", []):
                self.reverse_deps[imp].add(relative)

        # Convert defaultdicts to regular dicts for output
        return {
            "forward": dict(self.forward_deps),
            "reverse": dict(self.reverse_deps)
        }

    def get_importers(self, file_path: str) -> Set[str]:
        """Get files that import this file.

        Args:
            file_path: File path to check.

        Returns:
            Set of files that import this one.
        """
        return self.reverse_deps.get(file_path, set()).copy()

    def get_imports(self, file_path: str) -> Set[str]:
        """Get files that this file imports.

        Args:
            file_path: File path to check.

        Returns:
            Set of files this one imports.
        """
        return self.forward_deps.get(file_path, set()).copy()

    def has_circular_dependency(self, file1: str, file2: str) -> bool:
        """Check if two files have circular dependency.

        Args:
            file1: First file path.
            file2: Second file path.

        Returns:
            True if circular dependency exists.
        """
        # BFS to detect cycle
        visited = set()
        queue = [file1]

        while queue:
            current = queue.pop(0)
            if current == file2:
                # Found path from file1 to file2
                # Now check if file2 imports file1
                return file1 in self.get_imports(file2)

            if current in visited:
                continue

            visited.add(current)
            queue.extend(self.get_imports(current))

        return False
