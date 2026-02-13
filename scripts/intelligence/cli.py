"""Unified CLI entry point for code intelligence system.

Provides commands:
- build: Build full intelligence index
- classify: Classification only
- deps: Dependencies only
- query: Query the index
- status: System health check
"""

import argparse
import sys
import json
from pathlib import Path

try:
    from scripts.intelligence.config import IntelligenceConfig
    from scripts.intelligence.components.classifier import Classifier
    from scripts.intelligence.components.dependency_graph import DependencyGraph
    from scripts.intelligence.components.symbol_index import SymbolIndex
    from scripts.intelligence.monitoring.system_monitor import SystemMonitor
    from scripts.intelligence.monitoring.context_estimator import ContextEstimator
    from scripts.intelligence.utils import json_utils
except ImportError:
    # Fallback for direct script execution
    from .config import IntelligenceConfig
    from .components.classifier import Classifier
    from .components.dependency_graph import DependencyGraph
    from .components.symbol_index import SymbolIndex
    from .monitoring.system_monitor import SystemMonitor
    from .monitoring.context_estimator import ContextEstimator
    from .utils import json_utils


class BuildOrchestrator:
    """Orchestrate the full build process."""

    def __init__(self, config_path: str = "catalog.yaml"):
        """Initialize orchestrator.

        Args:
            config_path: Path to configuration file.
        """
        self.config = IntelligenceConfig(config_path)
        self.root_dir = "."

    def build_full(self) -> int:
        """Execute full build process.

        Returns:
            Exit code (0=success, 1=config error, 2=file error, 3=partial).
        """
        print("🔨 Starting build...")

        # Run classifier
        print("📂 Classifying files...")
        classifier = Classifier(self.config.config_path)
        classifications = classifier.classify_all(self.root_dir)

        # Run dependency analysis
        print("🔗 Analyzing dependencies...")
        dep_graph = DependencyGraph()
        dep_data = dep_graph.build_graph(self.root_dir)

        # Run symbol extraction
        print("🔍 Extracting symbols...")
        symbol_index = SymbolIndex()
        symbols = symbol_index.build_index(self.root_dir)

        # System health
        print("💚 Checking system health...")
        monitor = SystemMonitor()
        health = monitor.get_system_health()

        # Build report
        index_size = {
            "symbols": len(symbols),
            "files": len(classifications),
            "dependencies": sum(len(deps) for deps in dep_data.get("forward", {}).values())
        }
        estimator = ContextEstimator()
        context_report = estimator.format_report(index_size)

        # Output results
        print(f"\n📊 System Health: Memory {health.memory_percent:.1f}%, "
              f"Disk {health.disk_free_gb:.1f}GB, CPU {health.cpu_percent:.1f}%")
        print(context_report)
        print(f"🔨 Build complete: {len(classifications)} files, "
              f"{len(symbols)} symbols, {index_size['dependencies']} dependencies")

        return 0

    def classify_only(self) -> int:
        """Run classification only.

        Returns:
            Exit code.
        """
        classifier = Classifier(self.config.config_path)
        classifications = classifier.classify_all(self.root_dir)
        print(f"Classified {len(classifications)} files")
        return 0

    def deps_only(self) -> int:
        """Run dependency analysis only.

        Returns:
            Exit code.
        """
        dep_graph = DependencyGraph()
        dep_data = dep_graph.build_graph(self.root_dir)
        print(f"Analyzed dependencies: {len(dep_data.get('forward', {}))} files")
        return 0

    def status(self) -> int:
        """Show system status.

        Returns:
            Exit code.
        """
        monitor = SystemMonitor()
        print(monitor.format_report())
        return 0


def query_index(query_args) -> int:
    """Handle query command.

    Args:
        query_args: Parsed query arguments.

    Returns:
        Exit code.
    """
    index_file = ".claude/intelligence/index.json"

    if not Path(index_file).exists():
        print(f"Error: Index file not found. Run 'build' first.")
        return 2

    index_data = json_utils.load_file(index_file)
    if not index_data:
        print(f"Error: Could not load index file.")
        return 2

    if query_args.summary:
        print(f"Total symbols: {len(index_data.get('symbols', []))}")
        print(f"Total files: {len(index_data.get('files', []))}")
        return 0

    # Additional query implementations would go here
    print("Query feature coming in Phase 2")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified code intelligence system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.intelligence build
  python -m scripts.intelligence classify --config catalog.yaml
  python -m scripts.intelligence status
  python -m scripts.intelligence query --summary
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # build command
    build_parser = subparsers.add_parser('build', help='Build intelligence index')
    build_parser.add_argument('--config', default='catalog.yaml', help='Config file')

    # classify command
    classify_parser = subparsers.add_parser('classify', help='Classification only')
    classify_parser.add_argument('--config', default='catalog.yaml', help='Config file')

    # deps command
    deps_parser = subparsers.add_parser('deps', help='Dependencies only')
    deps_parser.add_argument('--config', default='catalog.yaml', help='Config file')

    # query command
    query_parser = subparsers.add_parser('query', help='Query the index')
    query_parser.add_argument('--file', help='Query specific file')
    query_parser.add_argument('--category', help='Query by category')
    query_parser.add_argument('--imports', help='Query forward dependencies')
    query_parser.add_argument('--depends-on', help='Query reverse dependencies')
    query_parser.add_argument('--summary', action='store_true', help='Stats only')

    # status command
    subparsers.add_parser('status', help='System health check')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        orchestrator = BuildOrchestrator(
            getattr(args, 'config', 'catalog.yaml')
        )

        if args.command == 'build':
            return orchestrator.build_full()
        elif args.command == 'classify':
            return orchestrator.classify_only()
        elif args.command == 'deps':
            return orchestrator.deps_only()
        elif args.command == 'status':
            return orchestrator.status()
        elif args.command == 'query':
            return query_index(args)
        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
