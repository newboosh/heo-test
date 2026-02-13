"""
Monitor index file sizes and performance metrics.

Logs warnings when indexes grow large enough to cause performance issues.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexMetrics:
    """Metrics for a single index file."""

    path: str
    size_bytes: int
    size_mb: float
    entry_count: int
    avg_entry_size: int
    load_time_ms: float


class IndexMonitor:
    """Monitor index health and flag performance issues."""

    # Thresholds
    WARNING_SIZE_MB = 10  # Warn at 10MB
    ERROR_SIZE_MB = 50  # Error at 50MB
    CRITICAL_SIZE_MB = 100  # Critical at 100MB

    MAX_LOAD_TIME_MS = 500  # Warn if loading takes > 500ms
    CRITICAL_LOAD_TIME_MS = 2000  # Error if > 2s

    # Memory thresholds (for context window)
    # Assume ~4 bytes per char, 1MB JSON ≈ 250k tokens roughly
    WARNING_TOKENS_APPROX = 50_000  # ~200KB
    ERROR_TOKENS_APPROX = 200_000  # ~800KB

    def __init__(self, index_dir: Path):
        """Initialize monitor.

        Args:
            index_dir: Directory containing index files
        """
        self.index_dir = index_dir
        self.metrics = {}

    def measure_index(self, index_path: Path) -> IndexMetrics:
        """Measure metrics for a single index file.

        Args:
            index_path: Path to index JSON file

        Returns:
            IndexMetrics with size, entry count, load time
        """
        import time

        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")

        # Measure file size
        size_bytes = index_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        # Measure load time
        start = time.time()
        try:
            with open(index_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted index: {index_path}: {e}")
            raise

        load_time_ms = (time.time() - start) * 1000

        # Count entries
        entry_count = self._count_entries(data)
        avg_entry_size = size_bytes // entry_count if entry_count > 0 else 0

        return IndexMetrics(
            path=str(index_path),
            size_bytes=size_bytes,
            size_mb=round(size_mb, 2),
            entry_count=entry_count,
            avg_entry_size=avg_entry_size,
            load_time_ms=round(load_time_ms, 2),
        )

    def _count_entries(self, data: dict) -> int:
        """Count entries in index structure.

        Args:
            data: Loaded index JSON

        Returns:
            Number of entries (symbols, files, etc.)
        """
        # Handle different index structures
        if "symbols" in data:
            # symbols.json: {"symbols": {"name": [...]}}
            return sum(len(v) if isinstance(v, list) else 1 for v in data["symbols"].values())
        elif "files" in data:
            # content_profile.json, metrics.json: {"files": {...}}
            return len(data["files"])
        elif "behaviors" in data:
            # test_behaviors.json: {"behaviors": {...}}
            return len(data["behaviors"])
        elif "links" in data:
            # links.json: {"links": [...]}
            return len(data["links"])
        else:
            # Unknown structure, count top-level keys
            return len(data)

    def check_index(self, index_path: Path) -> tuple[str, list[str]]:
        """Check index health and return status + warnings.

        Args:
            index_path: Path to index file

        Returns:
            Tuple of (status, warnings)
            Status: "ok", "warning", "error", "critical"
            Warnings: List of warning messages
        """
        try:
            metrics = self.measure_index(index_path)
            self.metrics[index_path.name] = metrics
        except Exception as e:
            return ("error", [f"Failed to read index: {e}"])

        warnings = []
        status = "ok"

        # Check size
        if metrics.size_mb >= self.CRITICAL_SIZE_MB:
            status = "critical"
            warnings.append(
                f"CRITICAL: Index size {metrics.size_mb}MB exceeds {self.CRITICAL_SIZE_MB}MB. "
                f"This will cause severe performance issues. Migrate to SQLite immediately."
            )
        elif metrics.size_mb >= self.ERROR_SIZE_MB:
            status = "error"
            warnings.append(
                f"ERROR: Index size {metrics.size_mb}MB exceeds {self.ERROR_SIZE_MB}MB. "
                f"Consider migrating to SQLite or implementing pagination."
            )
        elif metrics.size_mb >= self.WARNING_SIZE_MB:
            status = max(status, "warning", key=lambda x: ["ok", "warning", "error", "critical"].index(x))
            warnings.append(
                f"WARNING: Index size {metrics.size_mb}MB approaching limit. "
                f"Monitor performance and consider optimization."
            )

        # Check load time
        if metrics.load_time_ms >= self.CRITICAL_LOAD_TIME_MS:
            status = "critical" if status != "critical" else status
            warnings.append(
                f"CRITICAL: Load time {metrics.load_time_ms}ms is unacceptable. "
                f"Index queries will be very slow."
            )
        elif metrics.load_time_ms >= self.MAX_LOAD_TIME_MS:
            status = max(status, "warning", key=lambda x: ["ok", "warning", "error", "critical"].index(x))
            warnings.append(
                f"WARNING: Load time {metrics.load_time_ms}ms is slow. "
                f"Consider caching or incremental loading."
            )

        # Estimate token count (very rough)
        approx_tokens = (metrics.size_bytes // 4)  # ~4 bytes per token
        if approx_tokens >= self.ERROR_TOKENS_APPROX:
            status = max(status, "error", key=lambda x: ["ok", "warning", "error", "critical"].index(x))
            warnings.append(
                f"ERROR: Index may consume ~{approx_tokens:,} tokens in context window. "
                f"This could fill Claude's context. Use selective loading."
            )
        elif approx_tokens >= self.WARNING_TOKENS_APPROX:
            if status == "ok":
                status = "warning"
            warnings.append(
                f"WARNING: Index may consume ~{approx_tokens:,} tokens if loaded fully. "
                f"Consider query-based loading instead of full index."
            )

        return (status, warnings)

    def check_all_indexes(self) -> dict:
        """Check all indexes in the directory.

        Returns:
            Dict with overall status and per-index results
        """
        index_files = [
            "symbols.json",
            "links.json",
            "test_behaviors.json",
            "metrics.json",
            "content_profile.json",
        ]

        results = {}
        overall_status = "ok"

        for filename in index_files:
            index_path = self.index_dir / filename
            if not index_path.exists():
                results[filename] = {"status": "missing", "warnings": []}
                continue

            status, warnings = self.check_index(index_path)
            results[filename] = {"status": status, "warnings": warnings}

            # Update overall status
            status_order = ["ok", "warning", "error", "critical"]
            if status_order.index(status) > status_order.index(overall_status):
                overall_status = status

        return {"overall_status": overall_status, "indexes": results, "metrics": self.metrics}

    def get_report(self) -> str:
        """Generate human-readable monitoring report.

        Returns:
            Formatted report string
        """
        results = self.check_all_indexes()

        lines = [
            "=" * 70,
            "INDEX HEALTH REPORT",
            "=" * 70,
            "",
            f"Overall Status: {results['overall_status'].upper()}",
            "",
        ]

        for filename, result in results["indexes"].items():
            status = result["status"]
            status_symbol = {"ok": "✓", "warning": "⚠", "error": "✗", "critical": "🔥", "missing": "-"}[status]

            lines.append(f"{status_symbol} {filename}: {status.upper()}")

            if filename in self.metrics:
                m = self.metrics[filename]
                lines.append(f"  Size: {m.size_mb}MB ({m.entry_count:,} entries)")
                lines.append(f"  Load time: {m.load_time_ms}ms")
                lines.append(f"  Avg entry size: {m.avg_entry_size} bytes")

            for warning in result["warnings"]:
                lines.append(f"  → {warning}")

            lines.append("")

        # Summary
        total_size = sum(m.size_mb for m in self.metrics.values())
        total_entries = sum(m.entry_count for m in self.metrics.values())
        lines.append("=" * 70)
        lines.append(f"Total: {total_size:.2f}MB across {total_entries:,} entries")
        lines.append("=" * 70)

        return "\n".join(lines)

    def log_to_file(self, output_path: Optional[Path] = None):
        """Write monitoring report to log file.

        Args:
            output_path: Where to write log. Defaults to index_dir/health.log
        """
        if output_path is None:
            output_path = self.index_dir / "health.log"

        report = self.get_report()
        output_path.write_text(report)
        logger.info(f"Health report written to {output_path}")


def main():
    """CLI entry point for index monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor index file health")
    parser.add_argument("--index-dir", type=Path, default="docs/indexes", help="Index directory")
    parser.add_argument("--log", type=Path, help="Write report to log file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    monitor = IndexMonitor(args.index_dir)

    if args.json:
        results = monitor.check_all_indexes()
        print(json.dumps(results, indent=2))
    else:
        report = monitor.get_report()
        print(report)

        if args.log:
            monitor.log_to_file(args.log)

    # Exit code based on status
    results = monitor.check_all_indexes()
    status_codes = {"ok": 0, "warning": 0, "error": 1, "critical": 2}
    sys.exit(status_codes.get(results["overall_status"], 1))


if __name__ == "__main__":
    main()
