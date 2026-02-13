"""Markdown utilities for reference extraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict, Optional, List, Set


class ExtractedRef(TypedDict):
    """A reference extracted from markdown."""

    text: str
    type: str  # "file", "symbol", "import"
    line: int


# Internal path roots - references starting with these are internal
INTERNAL_ROOTS = ("app/", "scripts/", "tests/", "docs/", "modules/")

# Patterns for extraction
BACKTICK_PATTERN = re.compile(r"`([^`]+)`")
FENCED_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\n(.*?)```", re.DOTALL)
FILE_PATH_PATTERN = re.compile(r"^[\w./\-_]+\.(py|md|json|yaml|yml|sh|sql)$")
IMPORT_PATTERN = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")
SYMBOL_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$")


def extract_references_from_markdown(
    filepath: str,
    known_symbols: set[str] | None = None,
) -> list[ExtractedRef]:
    """Extract code references from a markdown file.

    Args:
        filepath: Path to markdown file
        known_symbols: Set of known symbol names from codebase

    Returns:
        List of extracted references
    """
    path = Path(filepath)
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    refs: list[ExtractedRef] = []
    seen: set[tuple[str, int]] = set()  # Dedupe by (text, line)

    if known_symbols is None:
        known_symbols = set()

    for line_num, line in enumerate(lines, start=1):
        # Skip lines inside fenced code blocks for backtick extraction
        # (we handle code blocks separately)

        # Extract backticked content
        for match in BACKTICK_PATTERN.finditer(line):
            text = match.group(1).strip()
            ref = _classify_reference(text, known_symbols)
            if ref and (text, line_num) not in seen:
                refs.append({
                    "text": text,
                    "type": ref,
                    "line": line_num,
                })
                seen.add((text, line_num))

    # Extract from fenced code blocks
    for match in FENCED_BLOCK_PATTERN.finditer(content):
        block_content = match.group(1)
        # Find line number of this block
        block_start = content[:match.start()].count("\n") + 1

        for i, block_line in enumerate(block_content.splitlines()):
            # Look for imports
            import_match = IMPORT_PATTERN.match(block_line.strip())
            if import_match:
                module = import_match.group(1) or import_match.group(2)
                if is_internal_reference(module, known_symbols):
                    line_num = block_start + i + 1
                    if (block_line.strip(), line_num) not in seen:
                        refs.append({
                            "text": block_line.strip(),
                            "type": "import",
                            "line": line_num,
                        })
                        seen.add((block_line.strip(), line_num))

    return refs


def _classify_reference(text: str, known_symbols: set[str]) -> str | None:
    """Classify a backticked reference.

    Returns:
        "file", "symbol", or None if not a valid internal reference
    """
    # Check if it's a file path
    if FILE_PATH_PATTERN.match(text):
        if is_internal_reference(text, known_symbols):
            return "file"
        return None

    # Check if it looks like a symbol
    if SYMBOL_PATTERN.match(text):
        # Remove trailing () if present
        symbol = text.rstrip("()")
        if symbol in known_symbols:
            return "symbol"
        # Could be a qualified name like module.function
        if "." in symbol:
            parts = symbol.split(".")
            # Check if any part is a known symbol
            if any(part in known_symbols for part in parts):
                return "symbol"
        return None

    # Check for qualified paths like app.auth.services.function
    if "." in text and not text.startswith("http"):
        parts = text.split(".")
        # If starts with internal module
        if parts[0] in ("app", "scripts", "tests", "modules"):
            return "symbol"

    return None


def is_internal_reference(text: str, known_symbols: set[str] | None = None) -> bool:
    """Check if a reference is internal to this codebase.

    Args:
        text: The reference text
        known_symbols: Set of known symbol names

    Returns:
        True if internal, False if external
    """
    if known_symbols is None:
        known_symbols = set()

    # File path starting with internal root
    if any(text.startswith(root) for root in INTERNAL_ROOTS):
        return True

    # Import from internal module
    if text.startswith("from app.") or text.startswith("import app."):
        return True
    if text.startswith("from scripts.") or text.startswith("import scripts."):
        return True
    if text.startswith("from tests.") or text.startswith("import tests."):
        return True

    # Module path starting with internal name
    if text.startswith("app.") or text.startswith("scripts.") or text.startswith("tests."):
        return True

    # Known symbol
    if text in known_symbols:
        return True

    # Symbol with () suffix
    if text.rstrip("()") in known_symbols:
        return True

    return False


def find_doc_section_for_ref(filepath: str, line: int) -> str | None:
    """Find the markdown section header containing a reference.

    Args:
        filepath: Path to markdown file
        line: Line number of reference

    Returns:
        Section header text, or None
    """
    path = Path(filepath)
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Walk backwards from the reference line to find nearest header
    for i in range(line - 1, -1, -1):
        if i < len(lines) and lines[i].startswith("#"):
            return lines[i].lstrip("#").strip()

    return None
