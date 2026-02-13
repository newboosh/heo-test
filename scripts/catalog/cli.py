"""Command-line interface for the catalog system."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Optional

from scripts.catalog.config import (
    load_config,
    ConfigError,
    CatalogConfig,
    DEFAULT_CONFIG_PATH,
    DEFAULT_STATE_PATH,
    TEMPLATE_CONFIG_PATH,
)
from scripts.catalog.classifier import classify_directory, FileClassification, ClassificationResult
from scripts.catalog.dependencies import build_dependency_graph, ModuleDependencies
from scripts.catalog.query import (
    load_classification_index,
    load_dependencies_index,
    query_by_category,
    query_by_file,
    query_depends_on,
    query_imports,
    get_summary,
)
from scripts.catalog.incremental import (
    load_state,
    save_state,
    get_changed_files,
    update_state_hashes,
    CatalogState,
)


class ExitCode(IntEnum):
    """Exit codes per R7 spec."""

    SUCCESS = 0
    CONFIG_ERROR = 1
    FILE_SYSTEM_ERROR = 2
    PARTIAL_SUCCESS = 3


def _get_config(config_path: Optional[str]) -> CatalogConfig:
    """Load config from path or use defaults.

    Search order:
    1. Explicit --config path
    2. .claude/catalog/config.yaml (new default)
    3. catalog.yaml (legacy fallback)
    4. Built-in defaults
    """
    if config_path:
        return load_config(config_path)

    # Try new default location first
    default_path = Path.cwd() / DEFAULT_CONFIG_PATH
    if default_path.exists():
        return load_config(default_path)

    # Legacy fallback
    legacy_path = Path.cwd() / "catalog.yaml"
    if legacy_path.exists():
        return load_config(legacy_path)

    return load_config(default_path)  # Will return defaults


def _get_state_path(root: Path) -> Path:
    """Get the state file path, ensuring parent directory exists."""
    state_path = root / DEFAULT_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    return state_path


def _ensure_output_dir(config: CatalogConfig, root: Path) -> Path:
    """Ensure output directory exists and return its path.

    Handles broken symlinks by removing them before creating the directory.
    """
    output_dir = root / config.output.index_dir

    # Handle broken symlinks: if path is a symlink but target doesn't exist
    if output_dir.is_symlink() and not output_dir.exists():
        output_dir.unlink()  # Remove broken symlink

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _build_classification_index(
    classifications: list[FileClassification],
) -> dict:
    """Build the classification index structure."""
    by_category: dict[str, int] = {}
    files: dict[str, dict] = {}

    for c in classifications:
        files[c.file_path] = {
            "primary_category": c.primary_category,
            "categories": c.categories,
            "matched_rules": c.matched_rules,
            "confidence": c.confidence,
        }

        # Count by primary category
        if c.primary_category not in by_category:
            by_category[c.primary_category] = 0
        by_category[c.primary_category] += 1

    return {
        "schema_version": "1.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "by_category": by_category,
        "files": files,
    }


def _build_dependencies_index(
    graph: dict[str, ModuleDependencies],
) -> dict:
    """Build the dependencies index structure."""
    modules: dict[str, dict] = {}

    for file_path, deps in graph.items():
        modules[file_path] = {
            "imports": deps.imports,
            "imported_by": deps.imported_by,
            "external": deps.external,
        }

    return {
        "schema_version": "1.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "module_count": len(modules),
        "modules": modules,
    }


def cmd_build(args: argparse.Namespace) -> int:
    """Build complete catalog (classification + dependencies)."""
    try:
        config = _get_config(args.config)
    except ConfigError as e:
        print(json.dumps(e.to_json()), file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    root = Path.cwd()
    output_dir = _ensure_output_dir(config, root)
    state_path = _get_state_path(root)
    incremental = getattr(args, "incremental", False)

    if incremental:
        print("Building catalog (incremental)...")
        state = load_state(state_path)
    else:
        print("Building catalog...")
        state = CatalogState()

    # Step 1: Classification
    print("  Classifying files...")
    class_result = classify_directory(root, config)
    classifications = class_result.classifications
    skipped_count = class_result.skipped_count

    # Check for changes if incremental mode
    if incremental and state.file_hashes:
        all_files = [c.file_path for c in classifications]
        changed = get_changed_files(root, all_files, state)
        if not changed:
            print("  No files changed since last build, skipping rebuild")
            # Still update state timestamps and return
            update_state_hashes(root, all_files, state)
            save_state(state, state_path)
            if skipped_count > 0:
                return ExitCode.PARTIAL_SUCCESS
            return ExitCode.SUCCESS
        print(f"  {len(changed)} files changed since last build")

    class_index = _build_classification_index(classifications)

    class_path = output_dir / config.output.classification_file
    class_path.write_text(json.dumps(class_index, indent=2))
    print(f"  Classified {class_index['file_count']} files")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} files due to errors")

    # Step 2: Dependencies
    print("  Analyzing dependencies...")
    python_files = [c.file_path for c in classifications if c.file_path.endswith(".py")]
    graph = build_dependency_graph(root, python_files)
    deps_index = _build_dependencies_index(graph)

    deps_path = output_dir / config.output.dependencies_file
    deps_path.write_text(json.dumps(deps_index, indent=2))
    print(f"  Analyzed {deps_index['module_count']} Python modules")

    # Save state for incremental builds
    all_files = [c.file_path for c in classifications]
    update_state_hashes(root, all_files, state)
    save_state(state, state_path)

    print(f"Output: {output_dir}")

    # Return PARTIAL_SUCCESS if any files were skipped
    if skipped_count > 0:
        return ExitCode.PARTIAL_SUCCESS
    return ExitCode.SUCCESS


def cmd_classify(args: argparse.Namespace) -> int:
    """Run classification only."""
    try:
        config = _get_config(args.config)
    except ConfigError as e:
        print(json.dumps(e.to_json()), file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    root = Path.cwd()
    output_dir = _ensure_output_dir(config, root)

    print("Classifying files...")
    class_result = classify_directory(root, config)
    classifications = class_result.classifications
    skipped_count = class_result.skipped_count
    class_index = _build_classification_index(classifications)

    class_path = output_dir / config.output.classification_file
    class_path.write_text(json.dumps(class_index, indent=2))

    print(f"Classified {class_index['file_count']} files")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} files due to errors")
    print(f"Output: {class_path}")

    # Return PARTIAL_SUCCESS if any files were skipped
    if skipped_count > 0:
        return ExitCode.PARTIAL_SUCCESS
    return ExitCode.SUCCESS


def cmd_deps(args: argparse.Namespace) -> int:
    """Run dependency analysis only."""
    try:
        config = _get_config(args.config)
    except ConfigError as e:
        print(json.dumps(e.to_json()), file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    root = Path.cwd()
    output_dir = _ensure_output_dir(config, root)

    print("Analyzing dependencies...")

    # Find all Python files
    python_files = []

    # Determine directories to scan
    if "." in config.index_dirs:
        scan_roots = [root]
    else:
        scan_roots = [root / d for d in config.index_dirs if (root / d).exists()]

    # Fallback to project root if no configured dirs exist
    if not scan_roots:
        scan_roots = [root]

    for scan_root in scan_roots:
        for py_file in scan_root.rglob("*.py"):
            try:
                relative = str(py_file.relative_to(root))
                # Skip files in skip_dirs (use path component matching, not substring)
                path_parts = Path(relative).parts
                if not any(skip in path_parts for skip in config.skip_dirs):
                    python_files.append(relative)
            except ValueError:
                continue

    graph = build_dependency_graph(root, python_files)
    deps_index = _build_dependencies_index(graph)

    deps_path = output_dir / config.output.dependencies_file
    deps_path.write_text(json.dumps(deps_index, indent=2))

    print(f"Analyzed {deps_index['module_count']} Python modules")
    print(f"Output: {deps_path}")
    return ExitCode.SUCCESS


def cmd_query(args: argparse.Namespace) -> int:
    """Query the catalog."""
    try:
        config = _get_config(args.config)
    except ConfigError as e:
        print(json.dumps(e.to_json()), file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    root = Path.cwd()
    output_dir = root / config.output.index_dir

    if args.file:
        # Query specific file
        class_path = output_dir / config.output.classification_file
        index = load_classification_index(class_path)
        if index is None:
            print("Classification index not found. Run 'catalog build' first.")
            return ExitCode.FILE_SYSTEM_ERROR

        result = query_by_file(index, args.file)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"File not found: {args.file}")

    elif args.category:
        # Query by category
        class_path = output_dir / config.output.classification_file
        index = load_classification_index(class_path)
        if index is None:
            print("Classification index not found. Run 'catalog build' first.")
            return ExitCode.FILE_SYSTEM_ERROR

        results = query_by_category(index, args.category)
        for r in results:
            print(r["file_path"])

    elif args.depends_on:
        # Query reverse dependencies
        deps_path = output_dir / config.output.dependencies_file
        index = load_dependencies_index(deps_path)
        if index is None:
            print("Dependencies index not found. Run 'catalog build' first.")
            return ExitCode.FILE_SYSTEM_ERROR

        results = query_depends_on(index, args.depends_on)
        if results:
            for r in results:
                print(r)
        else:
            print(f"No files depend on: {args.depends_on}")

    elif getattr(args, "imports", None):
        # Query forward dependencies (what does this file import?)
        deps_path = output_dir / config.output.dependencies_file
        index = load_dependencies_index(deps_path)
        if index is None:
            print("Dependencies index not found. Run 'catalog build' first.")
            return ExitCode.FILE_SYSTEM_ERROR

        result = query_imports(index, args.imports)
        if result:
            # Print internal imports
            for imp in result.get("imports", []):
                print(imp)
            # Print external imports with marker
            for ext in result.get("external", []):
                print(f"[external] {ext}")
        else:
            print(f"No imports found for: {args.imports}")

    elif getattr(args, "summary", False):
        # Summary statistics
        class_path = output_dir / config.output.classification_file
        index = load_classification_index(class_path)
        if index is None:
            print("Classification index not found. Run 'catalog build' first.")
            return ExitCode.FILE_SYSTEM_ERROR

        summary = get_summary(index)
        print(json.dumps(summary, indent=2))

    else:
        print("Please specify --file, --category, --imports, --depends-on, or --summary")
        return ExitCode.CONFIG_ERROR

    return ExitCode.SUCCESS


def cmd_status(args: argparse.Namespace) -> int:
    """Show catalog status."""
    try:
        config = _get_config(args.config)
    except ConfigError as e:
        print(json.dumps(e.to_json()), file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    root = Path.cwd()
    output_dir = root / config.output.index_dir

    print("Catalog Status")
    print("=" * 40)

    # Check classification index
    class_path = output_dir / config.output.classification_file
    class_index = load_classification_index(class_path)

    if class_index:
        summary = get_summary(class_index)
        print(f"\nClassification Index: {class_path}")
        print(f"  Generated: {summary['generated']}")
        print(f"  Files: {summary['file_count']}")
        print("  By category:")
        for cat, count in summary.get("by_category", {}).items():
            print(f"    {cat}: {count}")
    else:
        print("\nClassification Index: NOT FOUND")
        print(f"  Expected at: {class_path}")

    # Check dependencies index
    deps_path = output_dir / config.output.dependencies_file
    deps_index = load_dependencies_index(deps_path)

    if deps_index:
        print(f"\nDependencies Index: {deps_path}")
        print(f"  Generated: {deps_index.get('generated', 'unknown')}")
        print(f"  Modules: {deps_index.get('module_count', 0)}")
    else:
        print("\nDependencies Index: NOT FOUND")
        print(f"  Expected at: {deps_path}")

    if not class_index and not deps_index:
        print("\nNo indexes found. Run 'catalog build' to create them.")

    return ExitCode.SUCCESS


def _find_template_path() -> Optional[Path]:
    """Find the catalog config template in various possible locations.

    Searches for the template in order of priority:
    1. CLAUDE_PLUGIN_ROOT environment variable
    2. Relative to this script (standard plugin structure)
    3. .claude directory in current working directory
    4. Home directory .claude installation

    Returns:
        Path to template if found, None otherwise.
    """
    template_rel = TEMPLATE_CONFIG_PATH  # "templates/catalog/catalog.yaml.template"

    # List of potential plugin root directories to check
    candidates: list[Path] = []

    # 1. Environment variable (explicit override)
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    # 2. Relative to this script (scripts/catalog/cli.py -> plugin root)
    #    Handles: plugin_root/scripts/catalog/cli.py
    script_path = Path(__file__).resolve()
    candidates.append(script_path.parent.parent.parent)

    # 3. Current working directory's .claude folder (plugin installed there)
    candidates.append(Path.cwd() / ".claude")

    # 4. Home directory .claude installation
    candidates.append(Path.home() / ".claude")

    # 5. Walk up from script to find templates/ directory
    current = script_path.parent
    for _ in range(5):  # Max 5 levels up
        if (current / "templates").is_dir():
            candidates.append(current)
            break
        current = current.parent

    # Check each candidate
    for candidate in candidates:
        template_path = candidate / template_rel
        if template_path.exists():
            return template_path

    return None


def cmd_init(_args: argparse.Namespace) -> int:
    """Initialize catalog in current project."""
    root = Path.cwd()

    # Create .claude/catalog directory structure
    catalog_dir = root / ".claude" / "catalog"
    indexes_dir = catalog_dir / "indexes"
    cache_dir = root / ".claude" / "cache"

    print("Initializing catalog system...")

    # Create directories
    indexes_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Created {catalog_dir}/")
    print(f"  Created {cache_dir}/")

    # Copy or create config file
    config_path = catalog_dir / "config.yaml"
    if config_path.exists():
        print(f"  Config already exists: {config_path}")
    else:
        # Look for template in multiple possible locations
        template_path = _find_template_path()

        copied = False
        if template_path:
            try:
                shutil.copy(template_path, config_path)
                print(f"  Created {config_path} from template")
                copied = True
            except (IOError, OSError) as e:
                print(f"  Warning: Could not copy template: {e}", file=sys.stderr)

        if not copied:
            # Create minimal config
            minimal_config = '''# Catalog Configuration
# See templates/catalog/catalog.yaml.template for full options

version: "1.0"

index_dirs: [src, lib, app, scripts]
skip_dirs: [__pycache__, .git, node_modules, .venv, .trees]

output:
  index_dir: .claude/catalog/indexes
  classification_file: file_classification.json
  dependencies_file: module_dependencies.json

classification:
  categories:
    - name: test
      rules:
        - {type: directory, pattern: "**/tests/**"}
        - {type: filename, pattern: "test_*.py"}

  default_category: "uncategorized"
  priority_order: [test]
'''
            config_path.write_text(minimal_config)
            print(f"  Created {config_path} with defaults")

    # Update .gitignore if needed
    gitignore_path = root / ".gitignore"
    cache_pattern = ".claude/cache/"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if cache_pattern not in content:
            with open(gitignore_path, "a") as f:
                f.write(f"\n# Catalog build cache\n{cache_pattern}\n")
            print(f"  Added {cache_pattern} to .gitignore")
    else:
        gitignore_path.write_text(f"# Catalog build cache\n{cache_pattern}\n")
        print(f"  Created .gitignore with {cache_pattern}")

    print("\nCatalog initialized! Next steps:")
    print("  1. Edit .claude/catalog/config.yaml to customize categories")
    print("  2. Run 'catalog build' to build the indexes")
    print("  3. Query with 'catalog query --category <name>'")

    return ExitCode.SUCCESS


def _add_config_arg(parser: argparse.ArgumentParser) -> None:
    """Add --config argument to a parser."""
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file (default: .claude/catalog/config.yaml)",
    )


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="catalog",
        description="File classification and dependency tracking for AI agents",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init command
    subparsers.add_parser(
        "init",
        help="Initialize catalog in current project",
    )

    # build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build complete catalog (classification + dependencies)",
    )
    _add_config_arg(build_parser)
    build_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process changed files since last build",
    )

    # classify command
    classify_parser = subparsers.add_parser(
        "classify",
        help="Run classification only",
    )
    _add_config_arg(classify_parser)

    # deps command
    deps_parser = subparsers.add_parser(
        "deps",
        help="Run dependency analysis only",
    )
    _add_config_arg(deps_parser)

    # query command
    query_parser = subparsers.add_parser(
        "query",
        help="Query the catalog",
    )
    _add_config_arg(query_parser)
    query_parser.add_argument("--file", help="Query specific file")
    query_parser.add_argument("--category", help="Query files in category")
    query_parser.add_argument("--imports", help="Query what a file imports (forward dependencies)")
    query_parser.add_argument("--depends-on", help="Query files that import this file (reverse dependencies)")
    query_parser.add_argument("--summary", action="store_true", help="Show summary stats without full data")

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show catalog status",
    )
    _add_config_arg(status_parser)

    args = parser.parse_args(argv)

    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "classify": cmd_classify,
        "deps": cmd_deps,
        "query": cmd_query,
        "status": cmd_status,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
