"""Symbol index component for extracting code symbols.

Pure Python AST parsing (no LSP) to extract:
- Functions and methods
- Classes
- Modules
- Constants

Stores symbol metadata: name, file, line, type, docstring, scope.
"""

import ast
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from scripts.intelligence.utils import ast_utils, file_utils


@dataclass
class Symbol:
    """Extracted symbol metadata."""

    name: str
    """Symbol name."""

    file: str
    """File path."""

    line: int
    """Line number where defined."""

    type: str
    """Symbol type: 'function', 'class', 'method', 'constant'."""

    docstring: Optional[str] = None
    """Docstring if available."""

    scope: Optional[str] = None
    """Scope for methods (e.g., 'ClassName.method_name')."""

    language: str = "python"
    """Programming language."""

    def to_dict(self) -> Dict:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return asdict(self)


class SymbolIndex:
    """Extract symbols from Python code."""

    def __init__(self):
        """Initialize empty index."""
        self.symbols: List[Symbol] = []

    def extract_symbols(self, file_path: str) -> List[Symbol]:
        """Extract symbols from Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of Symbol objects extracted from file.
        """
        tree = ast_utils.parse_python_file(file_path)
        if not tree:
            return []

        symbols = []

        # Extract top-level functions and classes
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                symbols.append(self._symbol_from_func(node, file_path))
            elif isinstance(node, ast.ClassDef):
                symbols.append(self._symbol_from_class(node, file_path))
                # Extract methods from class
                symbols.extend(self._extract_methods(node, file_path))

        return symbols

    def build_index(self, root_dir: str) -> List[Symbol]:
        """Build complete symbol index for directory.

        Args:
            root_dir: Root directory to scan.

        Returns:
            Complete list of symbols.
        """
        self.symbols = []

        for python_file in file_utils.get_python_files(root_dir):
            symbols = self.extract_symbols(python_file)
            self.symbols.extend(symbols)

        return self.symbols

    @staticmethod
    def _symbol_from_func(node: ast.FunctionDef, file_path: str) -> Symbol:
        """Create Symbol from FunctionDef node.

        Args:
            node: FunctionDef AST node.
            file_path: File path.

        Returns:
            Symbol object.
        """
        return Symbol(
            name=node.name,
            file=file_path,
            line=node.lineno,
            type="function",
            docstring=ast_utils.get_docstring(node),
            language="python"
        )

    @staticmethod
    def _symbol_from_class(node: ast.ClassDef, file_path: str) -> Symbol:
        """Create Symbol from ClassDef node.

        Args:
            node: ClassDef AST node.
            file_path: File path.

        Returns:
            Symbol object.
        """
        return Symbol(
            name=node.name,
            file=file_path,
            line=node.lineno,
            type="class",
            docstring=ast_utils.get_docstring(node),
            language="python"
        )

    @staticmethod
    def _extract_methods(class_node: ast.ClassDef, file_path: str) -> List[Symbol]:
        """Extract methods from class.

        Args:
            class_node: ClassDef node.
            file_path: File path.

        Returns:
            List of Symbol objects for methods.
        """
        methods = []
        for method_node in ast_utils.get_class_methods(class_node):
            methods.append(Symbol(
                name=method_node.name,
                file=file_path,
                line=method_node.lineno,
                type="method",
                scope=f"{class_node.name}.{method_node.name}",
                docstring=ast_utils.get_docstring(method_node),
                language="python"
            ))
        return methods

    def search(self, name: str) -> List[Symbol]:
        """Search symbols by name.

        Args:
            name: Symbol name to search for.

        Returns:
            List of matching symbols.
        """
        return [s for s in self.symbols if name.lower() in s.name.lower()]

    def search_by_type(self, symbol_type: str) -> List[Symbol]:
        """Search symbols by type.

        Args:
            symbol_type: Type to search for (function, class, method).

        Returns:
            List of matching symbols.
        """
        return [s for s in self.symbols if s.type == symbol_type]

    def to_list(self) -> List[Dict]:
        """Convert to list of dictionaries.

        Returns:
            List representation of symbols.
        """
        return [s.to_dict() for s in self.symbols]
