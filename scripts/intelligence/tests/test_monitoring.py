"""Tests for system monitoring and context estimation.

Tests:
- System resource monitoring (memory, disk, CPU)
- Threshold checking and warning generation
- Context window impact estimation
- Model recommendations
"""

import pytest
from unittest.mock import patch, MagicMock
from scripts.intelligence.monitoring.system_monitor import SystemMonitor, SystemHealth
from scripts.intelligence.monitoring.context_estimator import ContextEstimator, ContextEstimate


class TestSystemMonitor:
    """Test system resource monitoring."""

    def test_init_defaults(self):
        """Test default threshold initialization."""
        monitor = SystemMonitor()
        assert monitor.memory_warn_pct == 75
        assert monitor.memory_critical_pct == 85
        assert monitor.disk_warn_gb == 5
        assert monitor.disk_critical_gb == 1

    def test_init_custom_thresholds(self):
        """Test custom threshold initialization."""
        monitor = SystemMonitor(
            memory_warn_pct=80,
            memory_critical_pct=90,
            disk_warn_gb=10,
            disk_critical_gb=2
        )
        assert monitor.memory_warn_pct == 80
        assert monitor.memory_critical_pct == 90
        assert monitor.disk_warn_gb == 10
        assert monitor.disk_critical_gb == 2

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_get_system_health(self, mock_psutil):
        """Test system health retrieval."""
        # Mock psutil values
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 4 * 1024 ** 2  # 4MB

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3  # 100GB
        mock_disk.percent = 50.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert isinstance(health, SystemHealth)
        assert health.memory_percent == 50.0
        assert health.memory_available_mb == 4.0
        assert health.disk_free_gb == 100.0
        assert health.disk_percent == 50.0
        assert health.cpu_percent == 25.0
        assert health.warnings == []

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_memory_warning(self, mock_psutil):
        """Test memory usage warning."""
        mock_memory = MagicMock()
        mock_memory.percent = 78.0  # Above 75% warn threshold
        mock_memory.available = 1 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3
        mock_disk.percent = 10.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert len(health.warnings) == 1
        assert "WARNING: Memory usage at 78.0%" in health.warnings[0]

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_memory_critical(self, mock_psutil):
        """Test memory critical alert."""
        mock_memory = MagicMock()
        mock_memory.percent = 88.0  # Above 85% critical threshold
        mock_memory.available = 0.5 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3
        mock_disk.percent = 10.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert len(health.warnings) == 1
        assert "CRITICAL: Memory usage at 88.0%" in health.warnings[0]

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_disk_warning(self, mock_psutil):
        """Test disk space warning."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 4 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 3 * 1024 ** 3  # 3GB free (below 5GB warn)
        mock_disk.percent = 90.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert len(health.warnings) == 1
        assert "WARNING: Only 3.0GB disk space free" in health.warnings[0]

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_disk_critical(self, mock_psutil):
        """Test disk critical alert."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 4 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 0.5 * 1024 ** 3  # 0.5GB free (below 1GB critical)
        mock_disk.percent = 99.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert len(health.warnings) == 1
        assert "CRITICAL: Only 0.5GB disk space free" in health.warnings[0]

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_is_healthy(self, mock_psutil):
        """Test healthy state check."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 4 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3
        mock_disk.percent = 10.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        assert monitor.is_healthy() is True

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_is_unhealthy(self, mock_psutil):
        """Test unhealthy state with critical warning."""
        mock_memory = MagicMock()
        mock_memory.percent = 88.0
        mock_memory.available = 0.5 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3
        mock_disk.percent = 10.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        assert monitor.is_healthy() is False


class TestContextEstimator:
    """Test context window impact estimation."""

    def test_init(self):
        """Test estimator initialization."""
        estimator = ContextEstimator()
        assert "haiku" in estimator.MODEL_BUDGETS
        assert "sonnet" in estimator.MODEL_BUDGETS
        assert "opus" in estimator.MODEL_BUDGETS

    def test_estimate_tokens_haiku(self):
        """Test token estimation for Haiku."""
        estimator = ContextEstimator()
        estimate = estimator.estimate_tokens({
            "symbols": 100,
            "files": 50,
            "dependencies": 200
        }, "haiku")

        assert estimate.model == "haiku"
        assert estimate.total_budget == 100_000
        # Base 500 + 100*20 + 50*15 + 200*10 = 500 + 2000 + 750 + 2000 = 5250
        assert estimate.estimated_tokens == 5250
        assert estimate.usage_percent == 5.25
        assert estimate.is_safe is True

    def test_estimate_tokens_sonnet(self):
        """Test token estimation for Sonnet."""
        estimator = ContextEstimator()
        estimate = estimator.estimate_tokens({
            "symbols": 1000,
            "files": 500,
            "dependencies": 2000
        }, "sonnet")

        assert estimate.model == "sonnet"
        assert estimate.total_budget == 200_000
        # Base 500 + 1000*20 + 500*15 + 2000*10 = 500 + 20000 + 7500 + 20000 = 48000
        assert estimate.estimated_tokens == 48000
        assert estimate.usage_percent == 24.0
        assert estimate.is_safe is True

    def test_estimate_tokens_unsafe(self):
        """Test unsafe token estimation (>50% of budget)."""
        estimator = ContextEstimator()
        estimate = estimator.estimate_tokens({
            "symbols": 3000,
            "files": 1000,
            "dependencies": 10000
        }, "haiku")

        # Base 500 + 3000*20 + 1000*15 + 10000*10 = 500 + 60000 + 15000 + 100000 = 175500
        assert estimate.estimated_tokens == 175500
        assert estimate.usage_percent == 175.5
        assert estimate.is_safe is False

    def test_estimate_tokens_unknown_model(self):
        """Test error on unknown model."""
        estimator = ContextEstimator()
        with pytest.raises(ValueError, match="Unknown model"):
            estimator.estimate_tokens({"symbols": 100}, "unknown")

    def test_recommend_model_small(self):
        """Test model recommendation for small index."""
        estimator = ContextEstimator()
        model = estimator.recommend_model({
            "symbols": 100,
            "files": 50,
            "dependencies": 200
        })
        # Both haiku and sonnet are safe, sonnet is bigger
        assert model in ["haiku", "sonnet"]

    def test_recommend_model_large(self):
        """Test model recommendation for large index."""
        estimator = ContextEstimator()
        model = estimator.recommend_model({
            "symbols": 3000,
            "files": 1000,
            "dependencies": 10000
        })
        # This will be too large for all, but should recommend the largest
        assert model in estimator.MODEL_BUDGETS

    def test_format_report(self):
        """Test report formatting."""
        estimator = ContextEstimator()
        report = estimator.format_report({
            "symbols": 100,
            "files": 50,
            "dependencies": 200
        }, "haiku")

        assert "Context impact" in report
        assert "5,250 tokens" in report or "5250 tokens" in report
        assert "5.2%" in report or "5.25%" in report
        assert "SAFE" in report
