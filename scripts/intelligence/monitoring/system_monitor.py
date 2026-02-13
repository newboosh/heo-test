"""System resource monitoring for intelligent build decisions.

Tracks:
- Memory usage (warn at 75%, critical at 85%)
- Disk space (warn at 5GB free, critical at 1GB)
- CPU usage (info only)
"""

import psutil
import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict


@dataclass
class SystemHealth:
    """System health metrics snapshot."""

    memory_percent: float
    """Memory usage as percentage (0-100)."""

    memory_available_mb: float
    """Available memory in MB."""

    disk_free_gb: float
    """Free disk space in GB."""

    disk_percent: float
    """Disk usage as percentage (0-100)."""

    cpu_percent: float
    """CPU usage as percentage (0-100)."""

    warnings: List[str]
    """List of warning messages."""


class SystemMonitor:
    """Monitor system resources and generate health reports.

    Tracks memory, disk, and CPU with configurable thresholds.
    """

    def __init__(self, memory_warn_pct: float = 75, memory_critical_pct: float = 85,
                 disk_warn_gb: float = 5, disk_critical_gb: float = 1):
        """Initialize system monitor with thresholds.

        Args:
            memory_warn_pct: Memory percentage to warn at (default 75).
            memory_critical_pct: Memory percentage for critical alert (default 85).
            disk_warn_gb: Free disk space (GB) to warn at (default 5).
            disk_critical_gb: Free disk space (GB) for critical alert (default 1).
        """
        self.memory_warn_pct = memory_warn_pct
        self.memory_critical_pct = memory_critical_pct
        self.disk_warn_gb = disk_warn_gb
        self.disk_critical_gb = disk_critical_gb

    def get_system_health(self) -> SystemHealth:
        """Get current system health metrics.

        Returns:
            SystemHealth with memory, disk, CPU metrics and warnings.
        """
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_mb = memory.available / (1024 ** 2)

        # Disk metrics (root filesystem)
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024 ** 3)
        disk_percent = disk.percent

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Check thresholds
        warnings = self._check_thresholds(memory_percent, disk_free_gb)

        return SystemHealth(
            memory_percent=memory_percent,
            memory_available_mb=memory_available_mb,
            disk_free_gb=disk_free_gb,
            disk_percent=disk_percent,
            cpu_percent=cpu_percent,
            warnings=warnings
        )

    def _check_thresholds(self, memory_percent: float, disk_free_gb: float) -> List[str]:
        """Check metrics against thresholds and generate warnings.

        Args:
            memory_percent: Current memory usage percentage.
            disk_free_gb: Current free disk space in GB.

        Returns:
            List of warning messages.
        """
        warnings = []

        # Memory warnings
        if memory_percent >= self.memory_critical_pct:
            warnings.append(f"CRITICAL: Memory usage at {memory_percent:.1f}%")
        elif memory_percent >= self.memory_warn_pct:
            warnings.append(f"WARNING: Memory usage at {memory_percent:.1f}%")

        # Disk warnings
        if disk_free_gb <= self.disk_critical_gb:
            warnings.append(f"CRITICAL: Only {disk_free_gb:.1f}GB disk space free")
        elif disk_free_gb <= self.disk_warn_gb:
            warnings.append(f"WARNING: Only {disk_free_gb:.1f}GB disk space free")

        return warnings

    def is_healthy(self) -> bool:
        """Check if system is in a healthy state (no critical warnings).

        Returns:
            True if no critical warnings.
        """
        health = self.get_system_health()
        for warning in health.warnings:
            if warning.startswith("CRITICAL"):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert health metrics to dictionary.

        Returns:
            Dictionary representation of SystemHealth.
        """
        health = self.get_system_health()
        return asdict(health)

    def to_json(self) -> str:
        """Convert health metrics to JSON string.

        Returns:
            JSON representation of SystemHealth.
        """
        return json.dumps(self.to_dict())

    def format_report(self) -> str:
        """Format health metrics as human-readable report.

        Returns:
            Formatted report string.
        """
        health = self.get_system_health()

        report = f"📊 System Health:\n"
        report += f"  Memory: {health.memory_percent:.1f}% ({health.memory_available_mb:.0f}MB available)\n"
        report += f"  Disk: {health.disk_free_gb:.1f}GB free ({health.disk_percent:.1f}% used)\n"
        report += f"  CPU: {health.cpu_percent:.1f}%\n"

        if health.warnings:
            report += f"  Warnings:\n"
            for warning in health.warnings:
                report += f"    - {warning}\n"

        return report
