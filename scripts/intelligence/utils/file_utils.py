"""File I/O utilities for code intelligence.

Provides helpers for:
- Reading and writing files
- Iterating over source files
- Filtering files by extension
"""

from pathlib import Path
from typing import Iterator, List, Set, Optional
import fnmatch


def read_file(file_path: str) -> Optional[str]:
    """Read file content safely.

    Args:
        file_path: Path to file.

    Returns:
        File content as string or None if read fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (FileNotFoundError, UnicodeDecodeError, PermissionError):
        return None


def write_file(file_path: str, content: str) -> bool:
    """Write content to file safely.

    Args:
        file_path: Path to file (creates directories if needed).
        content: Content to write.

    Returns:
        True if successful, False otherwise.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except (IOError, PermissionError):
        return False


def iterate_files(root_dir: str, extensions: Optional[Set[str]] = None,
                 exclude_patterns: Optional[List[str]] = None) -> Iterator[str]:
    """Iterate over files in directory tree.

    Args:
        root_dir: Root directory to search.
        extensions: Set of file extensions to include (e.g., {'.py', '.ts'}).
                   If None, include all files.
        exclude_patterns: Glob patterns to exclude (e.g., ['*.pyc', '__pycache__/*']).

    Yields:
        Absolute paths to matching files.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    root = Path(root_dir)
    if not root.exists():
        return

    for file_path in root.rglob('*'):
        if not file_path.is_file():
            continue

        # Check extension filter
        if extensions and file_path.suffix not in extensions:
            continue

        # Check exclude patterns
        relative = str(file_path.relative_to(root))
        if any(fnmatch.fnmatch(relative, pattern) for pattern in exclude_patterns):
            continue

        yield str(file_path)


def get_python_files(root_dir: str) -> Iterator[str]:
    """Get all Python files in directory tree.

    Excludes __pycache__, .pyc files, and virtual environments.

    Args:
        root_dir: Root directory to search.

    Yields:
        Absolute paths to .py files.
    """
    exclude = [
        '__pycache__/*',
        '*.pyc',
        '.venv/*',
        'venv/*',
        '.env/*',
        '.git/*'
    ]
    yield from iterate_files(root_dir, extensions={'.py'}, exclude_patterns=exclude)


def get_typescript_files(root_dir: str) -> Iterator[str]:
    """Get all TypeScript files in directory tree.

    Args:
        root_dir: Root directory to search.

    Yields:
        Absolute paths to .ts and .tsx files.
    """
    exclude = ['node_modules/*', '.git/*', 'dist/*', 'build/*']
    yield from iterate_files(root_dir, extensions={'.ts', '.tsx'}, exclude_patterns=exclude)


def get_javascript_files(root_dir: str) -> Iterator[str]:
    """Get all JavaScript files in directory tree.

    Args:
        root_dir: Root directory to search.

    Yields:
        Absolute paths to .js and .jsx files.
    """
    exclude = ['node_modules/*', '.git/*', 'dist/*', 'build/*']
    yield from iterate_files(root_dir, extensions={'.js', '.jsx'}, exclude_patterns=exclude)


def file_size(file_path: str) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file.

    Returns:
        File size or 0 if file doesn't exist.
    """
    try:
        return Path(file_path).stat().st_size
    except (FileNotFoundError, OSError):
        return 0


def file_exists(file_path: str) -> bool:
    """Check if file exists.

    Args:
        file_path: Path to file.

    Returns:
        True if file exists and is a file.
    """
    return Path(file_path).is_file()


def dir_exists(dir_path: str) -> bool:
    """Check if directory exists.

    Args:
        dir_path: Path to directory.

    Returns:
        True if directory exists.
    """
    return Path(dir_path).is_dir()


def get_relative_path(file_path: str, root_dir: str) -> str:
    """Get relative path from root directory.

    Args:
        file_path: Absolute file path.
        root_dir: Root directory.

    Returns:
        Relative path.
    """
    try:
        return str(Path(file_path).relative_to(root_dir))
    except ValueError:
        return file_path
