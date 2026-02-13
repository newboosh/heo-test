"""Extract code references from documentation files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Set

from scripts.librarian.symbol_indexer import load_index, get_known_symbols
from scripts.librarian.utils.markdown_utils import extract_references_from_markdown


class RefEntry(TypedDict):
    """A single reference entry."""

    text: str
    type: str
    line: int


class ExtractedRefs(TypedDict):
    """All extracted references."""

    generated: str
    doc_count: int
    ref_count: int
    docs: dict[str, list[RefEntry]]


# Directories to scan for docs
DOC_DIRS = ["docs"]

# Skip these directories
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "indexes"}

# Output path
REFS_PATH = Path("docs/indexes/extracted_refs.json")


def extract_all_references(
    root: Path | None = None,
    doc_dirs: list[str] | None = None,
    known_symbols: set[str] | None = None,
) -> ExtractedRefs:
    """Extract references from all documentation files.

    Args:
        root: Root directory
        doc_dirs: Directories containing docs
        known_symbols: Set of known symbol names (loads from index if None)

    Returns:
        Extracted references dictionary
    """
    if root is None:
        root = Path.cwd()
    if doc_dirs is None:
        doc_dirs = DOC_DIRS

    # Load symbols if not provided
    if known_symbols is None:
        index = load_index()
        known_symbols = get_known_symbols(index) if index else set()

    docs: dict[str, list[RefEntry]] = {}
    ref_count = 0

    for dir_name in doc_dirs:
        dir_path = root / dir_name
        if not dir_path.exists():
            continue

        for md_file in dir_path.rglob("*.md"):
            # Skip unwanted directories
            if any(skip in md_file.parts for skip in SKIP_DIRS):
                continue

            rel_path = str(md_file.relative_to(root))
            refs = extract_references_from_markdown(str(md_file), known_symbols)

            if refs:
                docs[rel_path] = refs
                ref_count += len(refs)

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "doc_count": len(docs),
        "ref_count": ref_count,
        "docs": docs,
    }


def save_refs(refs: ExtractedRefs, path: Path | None = None) -> None:
    """Save extracted references to JSON file.

    Args:
        refs: Extracted references
        path: Output path
    """
    if path is None:
        path = REFS_PATH

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(refs, indent=2), encoding="utf-8")


def load_refs(path: Path | None = None) -> ExtractedRefs | None:
    """Load extracted references from JSON file.

    Args:
        path: Input path

    Returns:
        Extracted references or None if not found
    """
    if path is None:
        path = REFS_PATH

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Extract and save references."""
    print("Extracting references from documentation...")
    refs = extract_all_references()
    save_refs(refs)
    print(f"Extracted {refs['ref_count']} references from {refs['doc_count']} docs")
    print(f"Saved to {REFS_PATH}")


if __name__ == "__main__":
    main()
