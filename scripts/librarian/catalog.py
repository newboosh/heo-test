"""Main catalog orchestrator - ties all librarian scripts together."""

import argparse
import sys
from pathlib import Path

from scripts.librarian.symbol_indexer import (
    build_symbol_index,
    save_index,
    load_index,
    INDEX_PATH,
)
from scripts.librarian.reference_extractor import (
    extract_all_references,
    save_refs,
    REFS_PATH,
)
from scripts.librarian.resolver import (
    resolve_all_references,
    save_links,
    load_links,
    LINKS_PATH,
)
from scripts.librarian.checker import (
    check_all_links,
    print_report,
    get_stale_links,
    get_broken_refs,
    get_error_refs,
)
from scripts.librarian.fixer import (
    gather_fix_context,
    save_fix_report,
    generate_fix_prompt,
)


def cmd_build(args: argparse.Namespace) -> int:
    """Build the complete catalog (index, extract, resolve)."""
    root = Path(args.root) if args.root else Path.cwd()

    print("=== Building Catalog ===\n")

    # Step 1: Build symbol index
    print("Step 1: Building symbol index...")
    symbol_index = build_symbol_index(root)
    save_index(symbol_index, path=root / INDEX_PATH)
    print(f"  Indexed {symbol_index['symbol_count']} symbols from {symbol_index['file_count']} files")
    print(f"  Saved to {root / INDEX_PATH}\n")

    # Step 2: Extract references
    print("Step 2: Extracting references from docs...")
    known_symbols = set(symbol_index["symbols"].keys())
    refs = extract_all_references(root, known_symbols=known_symbols)
    save_refs(refs, path=root / REFS_PATH)
    print(f"  Extracted {refs['ref_count']} references from {refs['doc_count']} docs")
    print(f"  Saved to {root / REFS_PATH}\n")

    # Step 3: Resolve references
    print("Step 3: Resolving references...")
    links = resolve_all_references(root, symbol_index)
    save_links(links, path=root / LINKS_PATH)
    print(f"  Resolved {links['total_links']} links")
    print(f"  Broken: {links['total_broken']}, Errors: {links['total_errors']}")
    print(f"  Saved to {root / LINKS_PATH}\n")

    print("=== Catalog Build Complete ===")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check links for staleness."""
    root = Path(args.root) if args.root else Path.cwd()

    print("=== Checking Links ===\n")

    links_index = load_links(path=root / LINKS_PATH)
    if links_index is None:
        print("Error: Links index not found. Run 'catalog build' first.")
        return 1

    updated_links, report = check_all_links(root, links_index)
    save_links(updated_links, path=root / LINKS_PATH)
    print_report(report)

    return 0 if report["stale"] == 0 else 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show catalog status."""
    root = Path(args.root) if args.root else Path.cwd()

    print("=== Catalog Status ===\n")

    # Check symbol index
    symbol_index = load_index(path=root / INDEX_PATH)
    if symbol_index:
        print(f"Symbol Index: {root / INDEX_PATH}")
        print(f"  Generated: {symbol_index['generated']}")
        print(f"  Symbols: {symbol_index['symbol_count']}")
        print(f"  Files: {symbol_index['file_count']}")
    else:
        print("Symbol Index: NOT FOUND")

    print()

    # Check links index
    links_index = load_links(path=root / LINKS_PATH)
    if links_index:
        print(f"Links Index: {root / LINKS_PATH}")
        print(f"  Generated: {links_index['generated']}")
        print(f"  Total links: {links_index['total_links']}")
        print(f"  Broken: {links_index['total_broken']}")
        print(f"  Errors: {links_index['total_errors']}")

        # Count stale if checked
        if "checked" in links_index:
            stale = get_stale_links(links_index)
            stale_count = sum(len(v) for v in stale.values())
            print(f"  Stale: {stale_count}")
            print(f"  Last checked: {links_index.get('checked', 'never')}")
    else:
        print("Links Index: NOT FOUND")

    print()

    # Summary
    if not symbol_index or not links_index:
        print("Run 'catalog build' to create the catalog.")
    elif links_index["total_broken"] > 0 or links_index["total_errors"] > 0:
        print("Issues found. Run 'catalog fix' to generate fix prompts.")
    else:
        print("Catalog is healthy.")

    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    """Generate fix context for issues."""
    root = Path(args.root) if args.root else Path.cwd()

    print("=== Gathering Fix Context ===\n")

    links_index = load_links(path=root / LINKS_PATH)
    if links_index is None:
        print("Error: Links index not found. Run 'catalog build' first.")
        return 1

    # First check for staleness
    updated_links, _ = check_all_links(root, links_index)
    save_links(updated_links, path=root / LINKS_PATH)

    # Gather fix context
    report = gather_fix_context(root, updated_links)
    save_fix_report(report)

    if report["total_issues"] == 0:
        print("No issues to fix. Catalog is up to date.")
        return 0

    print(f"Found {report['total_issues']} issues:")
    print(f"  Stale: {report['stale']}")
    print(f"  Broken: {report['broken']}")
    print(f"  Ambiguous: {report['errors']}")
    print()

    # Output fix prompts
    print("=== Fix Prompts for Librarian Agent ===\n")
    for issue in report["issues"]:
        prompt = generate_fix_prompt(issue)
        print(prompt)
        print("\n" + "=" * 60 + "\n")

    print(f"Saved fix report to docs/indexes/fix_report.json")
    print("\nInvoke the librarian agent to apply these fixes.")

    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    """Rebuild catalog from scratch."""
    # Just run build - it overwrites everything
    return cmd_build(args)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Catalog - Documentation reference management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  build     Build the complete catalog (index, extract, resolve)
  check     Check links for staleness
  status    Show catalog status
  fix       Generate fix prompts for issues
  rebuild   Rebuild catalog from scratch

Examples:
  python -m scripts.librarian.catalog build
  python -m scripts.librarian.catalog check
  python -m scripts.librarian.catalog status
  python -m scripts.librarian.catalog fix
        """,
    )

    parser.add_argument(
        "command",
        choices=["build", "check", "status", "fix", "rebuild"],
        help="Command to run",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Root directory (defaults to current directory)",
    )

    args = parser.parse_args()

    commands = {
        "build": cmd_build,
        "check": cmd_check,
        "status": cmd_status,
        "fix": cmd_fix,
        "rebuild": cmd_rebuild,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
