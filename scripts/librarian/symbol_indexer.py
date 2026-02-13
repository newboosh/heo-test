"""Build index of all defined symbols in the codebase."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional, List, Dict

from scripts.librarian.utils.ast_utils import extract_symbols_from_file


class SymbolEntry(TypedDict):
    """Entry for a symbol in the index."""

    file: str
    line: int
    type: str
    signature: str


class SymbolIndex(TypedDict):
    """The complete symbol index."""

    generated: str
    symbol_count: int
    file_count: int
    symbols: dict[str, list[SymbolEntry]]


# Directories to index
INDEX_DIRS = ["app", "scripts"]

# Directories to skip
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".tox"}

# Output path
INDEX_PATH = Path("docs/indexes/symbols.json")


def build_symbol_index(
    root: Path | None = None,
    index_dirs: list[str] | None = None,
) -> SymbolIndex:
    """Build index of all symbols in the codebase.

    Args:
        root: Root directory (defaults to current working directory)
        index_dirs: Directories to index (defaults to INDEX_DIRS)

    Returns:
        Symbol index dictionary
    """
    if root is None:
        root = Path.cwd()
    if index_dirs is None:
        index_dirs = INDEX_DIRS

    symbols: dict[str, list[SymbolEntry]] = {}
    file_count = 0

    for dir_name in index_dirs:
        dir_path = root / dir_name
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip unwanted directories
            if any(skip in py_file.parts for skip in SKIP_DIRS):
                continue

            # Get relative path
            rel_path = str(py_file.relative_to(root))
            file_count += 1

            # Extract symbols
            file_symbols = extract_symbols_from_file(str(py_file))

            for sym in file_symbols:
                name = sym["name"]
                entry: SymbolEntry = {
                    "file": rel_path,
                    "line": sym["line"],
                    "type": sym["type"],
                    "signature": sym["signature"],
                }

                if name not in symbols:
                    symbols[name] = []
                symbols[name].append(entry)

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "symbol_count": sum(len(entries) for entries in symbols.values()),
        "file_count": file_count,
        "symbols": symbols,
    }


def save_index(index: SymbolIndex, path: Path | None = None) -> None:
    """Save symbol index to JSON file.

    Args:
        index: The symbol index
        path: Output path (defaults to INDEX_PATH)
    """
    if path is None:
        path = INDEX_PATH

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def load_index(path: Path | None = None) -> SymbolIndex | None:
    """Load symbol index from JSON file.

    Args:
        path: Input path (defaults to INDEX_PATH)

    Returns:
        Symbol index or None if not found
    """
    if path is None:
        path = INDEX_PATH

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def get_known_symbols(index: SymbolIndex) -> set[str]:
    """Extract set of known symbol names from index.

    Args:
        index: Symbol index

    Returns:
        Set of symbol names
    """
    return set(index["symbols"].keys())


def main() -> None:
    """Build and save symbol index."""
    print("Building symbol index...")
    index = build_symbol_index()
    save_index(index)
    print(f"Indexed {index['symbol_count']} symbols from {index['file_count']} files")
    print(f"Saved to {INDEX_PATH}")


if __name__ == "__main__":
    main()
