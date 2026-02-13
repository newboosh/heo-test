"""AST utilities for symbol extraction and hashing."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import TypedDict, Union, Optional, List


class SymbolInfo(TypedDict):
    """Information about a code symbol."""

    name: str
    type: str  # "function", "class", "constant"
    file: str
    line: int
    signature: str


def extract_symbols_from_file(filepath: str) -> list[SymbolInfo]:
    """Extract all defined symbols from a Python file.

    Args:
        filepath: Path to the Python file

    Returns:
        List of symbol information dictionaries
    """
    path = Path(filepath)
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    symbols: list[SymbolInfo] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({
                "name": node.name,
                "type": "function",
                "file": filepath,
                "line": node.lineno,
                "signature": _get_function_signature(node),
            })

        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "name": node.name,
                "type": "class",
                "file": filepath,
                "line": node.lineno,
                "signature": f"class {node.name}",
            })
            # Also extract methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({
                        "name": f"{node.name}.{item.name}",
                        "type": "method",
                        "file": filepath,
                        "line": item.lineno,
                        "signature": _get_function_signature(item),
                    })

        elif isinstance(node, ast.Assign):
            # Module-level constants (UPPER_CASE convention)
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append({
                        "name": target.id,
                        "type": "constant",
                        "file": filepath,
                        "line": node.lineno,
                        "signature": target.id,
                    })

    return symbols


def _get_function_signature(node: (ast.FunctionDef, ast.AsyncFunctionDef)) -> str:
    """Extract function signature from AST node."""
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {ast.unparse(arg.annotation)}"
        args.append(arg_str)

    # Add *args
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")

    # Add **kwargs
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")

    signature = f"def {node.name}({', '.join(args)})"

    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"

    return signature


def hash_file(filepath: str) -> str | None:
    """Compute SHA256 hash of file content.

    Args:
        filepath: Path to file

    Returns:
        Hex digest of hash, or None if file not found
    """
    path = Path(filepath)
    if not path.exists():
        return None

    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def hash_symbol(filepath: str, symbol_name: str) -> str | None:
    """Compute hash of a specific symbol's AST.

    Hashes the AST structure, not raw text, so formatting changes
    don't affect the hash.

    Args:
        filepath: Path to Python file
        symbol_name: Name of function/class to hash (can be "Class.method")

    Returns:
        Hex digest of hash, or None if not found
    """
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return None

    # Handle method names like "ClassName.method_name"
    parts = symbol_name.split(".")
    if len(parts) == 2:
        class_name, method_name = parts
        return _hash_method(tree, class_name, method_name)

    # Find the symbol
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == symbol_name:
                return _hash_ast_node(node)

        elif isinstance(node, ast.ClassDef):
            if node.name == symbol_name:
                return _hash_ast_node(node)

    return None


def _hash_method(
    tree: ast.Module,
    class_name: str,
    method_name: str,
) -> str | None:
    """Hash a specific method within a class."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        return _hash_ast_node(item)
    return None


def _hash_ast_node(node: ast.AST) -> str:
    """Hash an AST node by dumping its structure."""
    # ast.dump produces a string representation of the AST
    # This ignores formatting but captures structure
    dumped = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dumped.encode()).hexdigest()


def get_symbol_source(filepath: str, symbol_name: str) -> str | None:
    """Get the source code of a specific symbol.

    Args:
        filepath: Path to Python file
        symbol_name: Name of function/class

    Returns:
        Source code string, or None if not found
    """
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return None

    lines = content.splitlines()

    # Handle method names
    parts = symbol_name.split(".")
    if len(parts) == 2:
        class_name, method_name = parts
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == method_name:
                            return _extract_source(lines, item)
        return None

    # Find top-level symbol
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == symbol_name:
                return _extract_source(lines, node)

        elif isinstance(node, ast.ClassDef):
            if node.name == symbol_name:
                return _extract_source(lines, node)

    return None


def _extract_source(lines: list[str], node: ast.AST) -> str:
    """Extract source lines for an AST node."""
    start = node.lineno - 1  # 0-indexed
    end = node.end_lineno if node.end_lineno else start + 1
    return "\n".join(lines[start:end])
