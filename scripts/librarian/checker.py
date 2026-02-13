"""Check links for staleness by comparing stored hashes to current state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Tuple

from scripts.librarian.resolver import load_links, save_links, LinksIndex
from scripts.librarian.utils.ast_utils import hash_file, hash_symbol


class CheckResult(TypedDict):
    """Result of checking a single link."""

    ref: str
    target: str
    status: str  # "CURRENT" or "STALE"
    stored_hash: str
    current_hash: str | None


class CheckReport(TypedDict):
    """Full check report."""

    checked: str
    total_checked: int
    current: int
    stale: int
    docs: dict[str, list[CheckResult]]


def check_all_links(
    root: Path | None = None,
    links_index: LinksIndex | None = None,
) -> tuple[LinksIndex, CheckReport]:
    """Check all links for staleness.

    Args:
        root: Root directory
        links_index: Links index (loads if None)

    Returns:
        Tuple of (updated links index, check report)
    """
    if root is None:
        root = Path.cwd()

    if links_index is None:
        links_index = load_links()
        if links_index is None:
            raise RuntimeError("Links index not found. Run resolver first.")

    report_docs: dict[str, list[CheckResult]] = {}
    total_checked = 0
    current_count = 0
    stale_count = 0

    for doc_path, doc_links in links_index["docs"].items():
        doc_results: list[CheckResult] = []

        for link in doc_links["links"]:
            current_hash = _compute_current_hash(link, root)

            if current_hash is None:
                # Target no longer exists - mark as stale
                status = "STALE"
                stale_count += 1
            elif current_hash == link["hash"]:
                status = "CURRENT"
                current_count += 1
            else:
                status = "STALE"
                stale_count += 1

            # Update the link with status
            link["status"] = status  # type: ignore

            doc_results.append({
                "ref": link["ref"],
                "target": link["target"],
                "status": status,
                "stored_hash": link["hash"],
                "current_hash": current_hash,
            })
            total_checked += 1

        if doc_results:
            report_docs[doc_path] = doc_results

    # Update the links index timestamp
    links_index["checked"] = datetime.now(timezone.utc).isoformat()  # type: ignore

    report: CheckReport = {
        "checked": datetime.now(timezone.utc).isoformat(),
        "total_checked": total_checked,
        "current": current_count,
        "stale": stale_count,
        "docs": report_docs,
    }

    return links_index, report


def _compute_current_hash(link: dict, root: Path) -> str | None:
    """Compute current hash for a link target.

    Args:
        link: Link dictionary with target and type
        root: Root directory

    Returns:
        Current hash or None if target not found
    """
    target = link["target"]
    link_type = link["type"]

    if link_type == "file":
        return hash_file(str(root / target))

    elif link_type in ("function", "class", "method", "constant"):
        # Target format: "path/to/file.py::symbol_name"
        if "::" in target:
            file_path, symbol_name = target.split("::", 1)
            symbol_hash = hash_symbol(str(root / file_path), symbol_name)
            if symbol_hash:
                return symbol_hash
            # Fall back to file hash if symbol extraction fails
            return hash_file(str(root / file_path))
        else:
            return hash_file(str(root / target))

    return None


def get_stale_links(links_index: LinksIndex) -> dict[str, list[dict]]:
    """Get all stale links from the index.

    Args:
        links_index: Links index

    Returns:
        Dictionary of doc path to list of stale links
    """
    stale: dict[str, list[dict]] = {}

    for doc_path, doc_links in links_index["docs"].items():
        doc_stale = [
            link for link in doc_links["links"]
            if link.get("status") == "STALE"
        ]
        if doc_stale:
            stale[doc_path] = doc_stale

    return stale


def get_broken_refs(links_index: LinksIndex) -> dict[str, list[dict]]:
    """Get all broken references from the index.

    Args:
        links_index: Links index

    Returns:
        Dictionary of doc path to list of broken refs
    """
    broken: dict[str, list[dict]] = {}

    for doc_path, doc_links in links_index["docs"].items():
        if doc_links["broken"]:
            broken[doc_path] = doc_links["broken"]

    return broken


def get_error_refs(links_index: LinksIndex) -> dict[str, list[dict]]:
    """Get all error references from the index.

    Args:
        links_index: Links index

    Returns:
        Dictionary of doc path to list of error refs
    """
    errors: dict[str, list[dict]] = {}

    for doc_path, doc_links in links_index["docs"].items():
        if doc_links["errors"]:
            errors[doc_path] = doc_links["errors"]

    return errors


def print_report(report: CheckReport) -> None:
    """Print check report to stdout."""
    print(f"\n=== Link Check Report ===")
    print(f"Checked: {report['checked']}")
    print(f"Total links: {report['total_checked']}")
    print(f"Current: {report['current']}")
    print(f"Stale: {report['stale']}")

    if report["stale"] > 0:
        print("\n--- Stale Links ---")
        for doc_path, results in report["docs"].items():
            stale_results = [r for r in results if r["status"] == "STALE"]
            if stale_results:
                print(f"\n{doc_path}:")
                for r in stale_results:
                    print(f"  - {r['ref']} → {r['target']}")


def main() -> None:
    """Check links and update index."""
    print("Checking links for staleness...")
    links_index, report = check_all_links()
    save_links(links_index)
    print_report(report)


if __name__ == "__main__":
    main()
