"""AST analysis for Python files."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional


def _parse_python_file(file_path: Path) -> Optional[ast.AST]:
    """Parse a Python file and return its AST.

    Returns None if the file cannot be parsed (not Python, syntax error, etc.)
    """
    if file_path.suffix.lower() != ".py":
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, IOError):
        return None


def _get_base_name(node: ast.expr) -> str:
    """Extract the full name from a base class node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        # Handle qualified names like pydantic.BaseModel
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _get_decorator_name(node: ast.expr) -> str:
    """Extract the full name from a decorator node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        # Handle qualified names like app.route or functools.lru_cache
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    elif isinstance(node, ast.Call):
        # Handle @decorator() or @decorator(args)
        return _get_decorator_name(node.func)
    return ""


def check_class_inherits(file_path: str | Path, name: str) -> bool:
    """Check if any class in the file inherits from the given name.

    Matches the syntactic name as written in the source file.
    Supports qualified names like 'pydantic.BaseModel'.

    Args:
        file_path: Path to the Python file.
        name: The base class name to look for.

    Returns:
        True if any class directly inherits from the specified name.
    """
    tree = _parse_python_file(Path(file_path))
    if tree is None:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = _get_base_name(base)
                if base_name == name:
                    return True

    return False


def check_decorator(file_path: str | Path, name: str) -> bool:
    """Check if any function or class has the given decorator.

    Matches the decorator name as written, ignoring arguments.
    Supports qualified names like 'app.route' or 'functools.lru_cache'.

    Args:
        file_path: Path to the Python file.
        name: The decorator name to look for.

    Returns:
        True if any function/class is decorated with the specified name.
    """
    tree = _parse_python_file(Path(file_path))
    if tree is None:
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                decorator_name = _get_decorator_name(decorator)
                if decorator_name == name:
                    return True

    return False


def check_has_main_block(file_path: str | Path) -> bool:
    """Check if file has a top-level if __name__ == '__main__' block.

    The comparison must be in the canonical form: __name__ on the left,
    "__main__" (with either quote style) on the right.

    Args:
        file_path: Path to the Python file.

    Returns:
        True if the file has a top-level main block.
    """
    tree = _parse_python_file(Path(file_path))
    if tree is None:
        return False

    # Only check top-level statements
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Compare):
                # Check: __name__ == "__main__"
                left = test.left
                if (
                    isinstance(left, ast.Name)
                    and left.id == "__name__"
                    and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.Eq)
                    and len(test.comparators) == 1
                ):
                    comp = test.comparators[0]
                    # Handle both ast.Str (Python <3.8) and ast.Constant (Python 3.8+)
                    if isinstance(comp, ast.Constant) and comp.value == "__main__":
                        return True
                    # For older Python versions
                    if hasattr(ast, 'Str') and isinstance(comp, ast.Str) and comp.s == "__main__":
                        return True

    return False


def match_ast_condition(file_path: str | Path, condition: str) -> bool:
    """Match a file against an AST condition.

    Supported conditions:
    - class_inherits:NAME - Check if any class inherits from NAME
    - decorator:NAME - Check if any function/class has decorator NAME
    - has_main_block - Check if file has if __name__ == '__main__'

    Args:
        file_path: Path to the Python file.
        condition: The condition string to check.

    Returns:
        True if the condition matches.
    """
    file_path = Path(file_path)

    # Only process Python files
    if file_path.suffix.lower() != ".py":
        return False

    if not condition:
        return False

    # Parse the condition
    if condition.startswith("class_inherits:"):
        name = condition[len("class_inherits:"):]
        return check_class_inherits(file_path, name)

    elif condition.startswith("decorator:"):
        name = condition[len("decorator:"):]
        return check_decorator(file_path, name)

    elif condition == "has_main_block":
        return check_has_main_block(file_path)

    # Unknown condition type
    return False
