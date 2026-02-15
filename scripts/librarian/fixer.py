"""Prepare fix context for the librarian agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, Optional, List, Dict

from scripts.librarian.resolver import load_links, LinksIndex
from scripts.librarian.checker import get_stale_links, get_broken_refs, get_error_refs
from scripts.librarian.utils.ast_utils import get_symbol_source
from scripts.librarian.utils.markdown_utils import find_doc_section_for_ref


class FixContext(TypedDict):
    """Context needed to fix a reference issue."""

    doc_path: str
    ref: str
    line: int
    issue_type: str  # "stale", "broken", "ambiguous"
    reason: str
    doc_section: str | None
    current_code: str | None
    candidates: list[str] | None


class FixReport(TypedDict):
    """Report of all issues needing fixes."""

    total_issues: int
    stale: int
    broken: int
    errors: int
    issues: list[FixContext]


def gather_fix_context(
    root: Path | None = None,
    links_index: LinksIndex | None = None,
) -> FixReport:
    """Gather context for all issues needing fixes.

    Args:
        root: Root directory
        links_index: Links index

    Returns:
        Fix report with context for each issue
    """
    if root is None:
        root = Path.cwd()

    if links_index is None:
        links_index = load_links()
        if links_index is None:
            raise RuntimeError("Links index not found. Run resolver first.")

    issues: list[FixContext] = []

    # Gather stale links
    stale = get_stale_links(links_index)
    for doc_path, links in stale.items():
        for link in links:
            context = _build_stale_context(doc_path, link, root)
            issues.append(context)

    # Gather broken refs
    broken = get_broken_refs(links_index)
    for doc_path, refs in broken.items():
        for ref in refs:
            context = _build_broken_context(doc_path, ref, root)
            issues.append(context)

    # Gather error refs (ambiguous)
    errors = get_error_refs(links_index)
    for doc_path, refs in errors.items():
        for ref in refs:
            context = _build_error_context(doc_path, ref, root)
            issues.append(context)

    return {
        "total_issues": len(issues),
        "stale": sum(1 for i in issues if i["issue_type"] == "stale"),
        "broken": sum(1 for i in issues if i["issue_type"] == "broken"),
        "errors": sum(1 for i in issues if i["issue_type"] == "ambiguous"),
        "issues": issues,
    }


def _build_stale_context(
    doc_path: str,
    link: dict,
    root: Path,
) -> FixContext:
    """Build context for a stale link."""
    # Get current code if it's a symbol reference
    current_code = None
    if "::" in link.get("target", ""):
        file_path, symbol_name = link["target"].split("::", 1)
        current_code = get_symbol_source(str(root / file_path), symbol_name)

    # Get the doc section where this reference appears
    doc_section = find_doc_section_for_ref(str(root / doc_path), link.get("line", 0))

    return {
        "doc_path": doc_path,
        "ref": link["ref"],
        "line": link.get("line", 0),
        "issue_type": "stale",
        "reason": "Code has changed since documentation was written",
        "doc_section": doc_section,
        "current_code": current_code,
        "candidates": None,
    }


def _build_broken_context(
    doc_path: str,
    ref: dict,
    root: Path,
) -> FixContext:
    """Build context for a broken reference."""
    # Try to find similar symbols/files that might be the renamed target
    candidates = _search_similar(ref["ref"], root)

    doc_section = find_doc_section_for_ref(str(root / doc_path), ref.get("line", 0))

    return {
        "doc_path": doc_path,
        "ref": ref["ref"],
        "line": ref.get("line", 0),
        "issue_type": "broken",
        "reason": ref.get("reason", "Reference not found"),
        "doc_section": doc_section,
        "current_code": None,
        "candidates": candidates,
    }


def _build_error_context(
    doc_path: str,
    ref: dict,
    root: Path,
) -> FixContext:
    """Build context for an error (ambiguous) reference."""
    doc_section = find_doc_section_for_ref(str(root / doc_path), ref.get("line", 0))

    return {
        "doc_path": doc_path,
        "ref": ref["ref"],
        "line": ref.get("line", 0),
        "issue_type": "ambiguous",
        "reason": ref.get("reason", "Ambiguous reference"),
        "doc_section": doc_section,
        "current_code": None,
        "candidates": ref.get("candidates", []),
    }


def _search_similar(ref: str, root: Path) -> list[str]:
    """Search for files/symbols similar to a broken reference.

    Simple implementation - looks for files with similar names.
    """
    candidates: list[str] = []

    # Extract the base name from the reference
    if "/" in ref:
        # File path - look for files with similar name
        base_name = Path(ref).stem
        for py_file in root.rglob("*.py"):
            if base_name.lower() in py_file.stem.lower():
                candidates.append(str(py_file.relative_to(root)))
    else:
        # Symbol - look in symbol index
        from scripts.librarian.symbol_indexer import load_index
        index = load_index()
        if index:
            ref_lower = ref.lower().rstrip("()")
            for symbol_name in index["symbols"]:
                if ref_lower in symbol_name.lower():
                    entries = index["symbols"][symbol_name]
                    for entry in entries:
                        candidates.append(f"{entry['file']}::{symbol_name}")

    return candidates[:5]  # Limit to 5 candidates


def generate_fix_prompt(context: FixContext) -> str:
    """Generate a prompt for the librarian agent to fix an issue.

    Args:
        context: Fix context

    Returns:
        Prompt string for the agent
    """
    prompt_parts = [
        f"Fix the following {context['issue_type']} reference in `{context['doc_path']}`:",
        f"",
        f"**Reference:** `{context['ref']}` (line {context['line']})",
        f"**Issue:** {context['reason']}",
    ]

    if context["doc_section"]:
        prompt_parts.append(f"**Section:** {context['doc_section']}")

    if context["issue_type"] == "stale" and context["current_code"]:
        prompt_parts.extend([
            "",
            "**Current code:**",
            "```python",
            context["current_code"],
            "```",
            "",
            "Update the documentation to accurately describe the current code.",
        ])

    elif context["issue_type"] == "broken" and context["candidates"]:
        prompt_parts.extend([
            "",
            "**Possible matches:**",
        ])
        for candidate in context["candidates"]:
            prompt_parts.append(f"- `{candidate}`")
        prompt_parts.extend([
            "",
            "Update the reference to point to the correct target, or remove it if no longer relevant.",
        ])

    elif context["issue_type"] == "ambiguous" and context["candidates"]:
        prompt_parts.extend([
            "",
            "**Ambiguous - found in multiple locations:**",
        ])
        for candidate in context["candidates"]:
            prompt_parts.append(f"- `{candidate}`")
        prompt_parts.extend([
            "",
            "Qualify the reference to be unambiguous (e.g., `app.auth.services.function_name`).",
        ])

    return "\n".join(prompt_parts)


def save_fix_report(report: FixReport, path: Path | None = None) -> None:
    """Save fix report to JSON file."""
    if path is None:
        path = Path("docs/indexes/fix_report.json")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    """Gather and display fix context."""
    print("Gathering fix context...")
    report = gather_fix_context()
    save_fix_report(report)

    print(f"\n=== Fix Report ===")
    print(f"Total issues: {report['total_issues']}")
    print(f"  Stale: {report['stale']}")
    print(f"  Broken: {report['broken']}")
    print(f"  Ambiguous: {report['errors']}")

    if report["issues"]:
        print("\n--- Issues ---")
        for issue in report["issues"]:
            print(f"\n{issue['doc_path']}:{issue['line']}")
            print(f"  {issue['issue_type'].upper()}: `{issue['ref']}`")
            print(f"  {issue['reason']}")

        print("\nTo fix these issues, run: python -m scripts.librarian.doclinks fix")


if __name__ == "__main__":
    main()
