"""AST utilities for analyzing Python code structure.

Provides helpers for:
- Walking AST nodes efficiently
- Extracting specific node types
- Converting AST to data structures
"""

import ast
from typing import List, Dict, Any, Optional, Type, Iterator
from pathlib import Path


def parse_python_file(file_path: str) -> Optional[ast.Module]:
    """Parse Python file into AST.

    Args:
        file_path: Path to Python file.

    Returns:
        AST Module node or None if parse fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return ast.parse(code)
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
        return None


def find_nodes(tree: ast.AST, node_type: Type[ast.AST]) -> List[ast.AST]:
    """Find all nodes of a specific type in AST.

    Args:
        tree: AST root node (usually Module).
        node_type: AST node class to find (e.g., ast.FunctionDef).

    Returns:
        List of matching nodes.
    """
    results = []
    for node in ast.walk(tree):
        if isinstance(node, node_type):
            results.append(node)
    return results


def get_function_defs(tree: ast.Module) -> List[ast.FunctionDef]:
    """Get all function definitions (top-level).

    Args:
        tree: Module AST.

    Returns:
        List of FunctionDef nodes.
    """
    return [node for node in tree.body if isinstance(node, ast.FunctionDef)]


def get_class_defs(tree: ast.Module) -> List[ast.ClassDef]:
    """Get all class definitions (top-level).

    Args:
        tree: Module AST.

    Returns:
        List of ClassDef nodes.
    """
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]


def get_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from node.

    Works for Module, FunctionDef, ClassDef, and their async variants.

    Args:
        node: AST node.

    Returns:
        Docstring text or None if not found.
    """
    docstring = ast.get_docstring(node)
    return docstring


def get_function_arguments(func_node: ast.FunctionDef) -> List[str]:
    """Extract argument names from function definition.

    Args:
        func_node: FunctionDef node.

    Returns:
        List of argument names.
    """
    args = func_node.args
    arg_names = [arg.arg for arg in args.args]

    if args.posonlyargs:
        arg_names = [arg.arg for arg in args.posonlyargs] + arg_names

    if args.vararg:
        arg_names.append(f"*{args.vararg.arg}")

    if args.kwonlyargs:
        arg_names.extend([arg.arg for arg in args.kwonlyargs])

    if args.kwarg:
        arg_names.append(f"**{args.kwarg.arg}")

    return arg_names


def get_class_methods(class_node: ast.ClassDef) -> List[ast.FunctionDef]:
    """Extract all methods from class definition.

    Args:
        class_node: ClassDef node.

    Returns:
        List of FunctionDef nodes.
    """
    return [node for node in class_node.body if isinstance(node, ast.FunctionDef)]


def get_class_bases(class_node: ast.ClassDef) -> List[str]:
    """Extract base class names from class definition.

    Args:
        class_node: ClassDef node.

    Returns:
        List of base class names (as strings, not full expressions).
    """
    bases = []
    for base in class_node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            # Handle module.Class format
            parts = []
            node = base
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            bases.append('.'.join(reversed(parts)))
    return bases


def get_imports(tree: ast.Module) -> Dict[str, List[str]]:
    """Extract all imports from module.

    Args:
        tree: Module AST.

    Returns:
        Dict with 'import' and 'from' keys listing imported names.
    """
    imports = {"import": [], "from": []}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports["import"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                module = node.module or ""
                imports["from"].append(f"{module}.{alias.name}" if module else alias.name)

    return imports


def get_function_calls(tree: ast.Module) -> List[str]:
    """Extract all function calls from module.

    Args:
        tree: Module AST.

    Returns:
        List of function names called.
    """
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # Handle obj.method() calls
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                calls.append('.'.join(reversed(parts)))

    return calls


def get_line_range(node: ast.AST) -> tuple[int, int]:
    """Get line range of AST node.

    Args:
        node: AST node.

    Returns:
        Tuple of (start_line, end_line).
    """
    start_line = node.lineno if hasattr(node, 'lineno') else 0
    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
    return (start_line, end_line)
