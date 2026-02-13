"""Resolve references to exact code locations and compute hashes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Union

from scripts.librarian.symbol_indexer import load_index, SymbolIndex
from scripts.librarian.reference_extractor import load_refs
from scripts.librarian.utils.ast_utils import hash_file, hash_symbol


class ResolvedLink(TypedDict):
    """A successfully resolved link."""

    ref: str
    target: str
    type: str  # "file", "function", "class", "method", "constant"
    hash: str
    line: int  # line in the doc where reference appears


class BrokenRef(TypedDict):
    """A reference that couldn't be resolved."""

    ref: str
    line: int
    reason: str


class ErrorRef(TypedDict):
    """A reference with errors (e.g., ambiguous)."""

    ref: str
    line: int
    reason: str
    candidates: list[str]


class DocLinks(TypedDict):
    """Links for a single document."""

    links: list[ResolvedLink]
    broken: list[BrokenRef]
    errors: list[ErrorRef]


class LinksIndex(TypedDict):
    """The complete links index."""

    generated: str
    total_links: int
    total_broken: int
    total_errors: int
    docs: dict[str, DocLinks]


# Output path
LINKS_PATH = Path("docs/indexes/links.json")

# Import pattern for parsing
IMPORT_PATTERN = re.compile(
    r"^(?:from\s+([\w.]+)\s+import\s+([\w,\s]+)|import\s+([\w.]+))"
)


def resolve_all_references(
    root: Path | None = None,
    symbols_index: SymbolIndex | None = None,
) -> LinksIndex:
    """Resolve all extracted references.

    Args:
        root: Root directory
        symbols_index: Symbol index (loads if None)

    Returns:
        Links index with resolved links, broken refs, and errors
    """
    if root is None:
        root = Path.cwd()

    # Load indices
    if symbols_index is None:
        symbols_index = load_index()
        if symbols_index is None:
            raise RuntimeError("Symbol index not found. Run symbol_indexer first.")

    refs_data = load_refs()
    if refs_data is None:
        raise RuntimeError("Extracted refs not found. Run reference_extractor first.")

    docs: dict[str, DocLinks] = {}
    total_links = 0
    total_broken = 0
    total_errors = 0

    for doc_path, refs in refs_data["docs"].items():
        doc_links: DocLinks = {
            "links": [],
            "broken": [],
            "errors": [],
        }

        for ref in refs:
            result = _resolve_single_ref(
                ref["text"],
                ref["type"],
                ref["line"],
                root,
                symbols_index,
            )

            if "hash" in result:
                doc_links["links"].append(result)  # type: ignore
                total_links += 1
            elif "candidates" in result:
                doc_links["errors"].append(result)  # type: ignore
                total_errors += 1
            else:
                doc_links["broken"].append(result)  # type: ignore
                total_broken += 1

        docs[doc_path] = doc_links

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_links": total_links,
        "total_broken": total_broken,
        "total_errors": total_errors,
        "docs": docs,
    }


def _resolve_single_ref(
    text: str,
    ref_type: str,
    line: int,
    root: Path,
    symbols: SymbolIndex,
) -> ResolvedLink | BrokenRef | ErrorRef:
    """Resolve a single reference.

    Args:
        text: Reference text
        ref_type: Type of reference ("file", "symbol", "import")
        line: Line number in doc
        root: Root directory
        symbols: Symbol index

    Returns:
        Resolved link, broken ref, or error
    """
    if ref_type == "file":
        return _resolve_file_ref(text, line, root)
    elif ref_type == "symbol":
        return _resolve_symbol_ref(text, line, root, symbols)
    elif ref_type == "import":
        return _resolve_import_ref(text, line, root, symbols)
    else:
        return {"ref": text, "line": line, "reason": f"unknown ref type: {ref_type}"}


def _resolve_file_ref(
    text: str,
    line: int,
    root: Path,
) -> ResolvedLink | BrokenRef:
    """Resolve a file path reference."""
    file_path = root / text

    if not file_path.exists():
        return {"ref": text, "line": line, "reason": "file not found"}

    file_hash = hash_file(str(file_path))
    if file_hash is None:
        return {"ref": text, "line": line, "reason": "could not hash file"}

    return {
        "ref": text,
        "target": text,
        "type": "file",
        "hash": file_hash,
        "line": line,
    }


def _resolve_symbol_ref(
    text: str,
    line: int,
    root: Path,
    symbols: SymbolIndex,
) -> ResolvedLink | BrokenRef | ErrorRef:
    """Resolve a symbol reference."""
    # Clean up symbol name (remove trailing parentheses)
    symbol_name = text.rstrip("()")

    # Check for qualified name (e.g., app.auth.services.function)
    if "." in symbol_name:
        return _resolve_qualified_symbol(symbol_name, line, root, symbols)

    # Look up in symbol index
    if symbol_name not in symbols["symbols"]:
        return {"ref": text, "line": line, "reason": "symbol not found"}

    entries = symbols["symbols"][symbol_name]

    # Ambiguous - multiple definitions
    if len(entries) > 1:
        candidates = [f"{e['file']}:{e['line']}" for e in entries]
        return {
            "ref": text,
            "line": line,
            "reason": f"ambiguous: found in {len(entries)} locations",
            "candidates": candidates,
        }

    # Single match - resolve
    entry = entries[0]
    target = f"{entry['file']}::{symbol_name}"

    # Hash the symbol
    symbol_hash = hash_symbol(str(root / entry["file"]), symbol_name)
    if symbol_hash is None:
        # Fall back to file hash
        symbol_hash = hash_file(str(root / entry["file"]))
        if symbol_hash is None:
            return {"ref": text, "line": line, "reason": "could not hash symbol"}

    return {
        "ref": text,
        "target": target,
        "type": entry["type"],
        "hash": symbol_hash,
        "line": line,
    }


def _resolve_qualified_symbol(
    qualified_name: str,
    line: int,
    root: Path,
    symbols: SymbolIndex,
) -> ResolvedLink | BrokenRef:
    """Resolve a qualified symbol like app.auth.services.function."""
    parts = qualified_name.split(".")

    # Try to find the symbol by just the last part
    symbol_name = parts[-1]

    if symbol_name not in symbols["symbols"]:
        return {"ref": qualified_name, "line": line, "reason": "symbol not found"}

    entries = symbols["symbols"][symbol_name]

    # Filter entries to those matching the module path
    # Convert app.auth.services to app/auth/services.py
    expected_path_parts = parts[:-1]
    expected_path = "/".join(expected_path_parts)

    matching = [e for e in entries if expected_path in e["file"]]

    if not matching:
        return {
            "ref": qualified_name,
            "line": line,
            "reason": f"symbol not found in module {expected_path}",
        }

    if len(matching) > 1:
        return {
            "ref": qualified_name,
            "line": line,
            "reason": "still ambiguous after qualification",
        }

    entry = matching[0]
    target = f"{entry['file']}::{symbol_name}"

    symbol_hash = hash_symbol(str(root / entry["file"]), symbol_name)
    if symbol_hash is None:
        symbol_hash = hash_file(str(root / entry["file"]))
        if symbol_hash is None:
            return {"ref": qualified_name, "line": line, "reason": "could not hash"}

    return {
        "ref": qualified_name,
        "target": target,
        "type": entry["type"],
        "hash": symbol_hash,
        "line": line,
    }


def _resolve_import_ref(
    text: str,
    line: int,
    root: Path,
    symbols: SymbolIndex,
) -> ResolvedLink | BrokenRef:
    """Resolve an import statement reference."""
    match = IMPORT_PATTERN.match(text)
    if not match:
        return {"ref": text, "line": line, "reason": "could not parse import"}

    if match.group(1):
        # from X import Y
        module = match.group(1)
        imported = match.group(2).split(",")[0].strip()  # Take first if multiple
    else:
        # import X
        module = match.group(3)
        imported = module.split(".")[-1]

    # Convert module path to file path
    module_path = module.replace(".", "/") + ".py"

    # Check if file exists
    if not (root / module_path).exists():
        # Try as package
        module_path = module.replace(".", "/") + "/__init__.py"
        if not (root / module_path).exists():
            return {"ref": text, "line": line, "reason": f"module not found: {module}"}

    # Hash the module file
    file_hash = hash_file(str(root / module_path))
    if file_hash is None:
        return {"ref": text, "line": line, "reason": "could not hash module"}

    return {
        "ref": text,
        "target": module_path,
        "type": "file",
        "hash": file_hash,
        "line": line,
    }


def save_links(links: LinksIndex, path: Path | None = None) -> None:
    """Save links index to JSON file."""
    if path is None:
        path = LINKS_PATH

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(links, indent=2), encoding="utf-8")


def load_links(path: Path | None = None) -> LinksIndex | None:
    """Load links index from JSON file."""
    if path is None:
        path = LINKS_PATH

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Resolve and save links."""
    print("Resolving references...")
    links = resolve_all_references()
    save_links(links)
    print(f"Resolved {links['total_links']} links")
    print(f"Broken: {links['total_broken']}, Errors: {links['total_errors']}")
    print(f"Saved to {LINKS_PATH}")


if __name__ == "__main__":
    main()
