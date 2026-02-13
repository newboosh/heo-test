"""Tests for the index health monitor module."""

import json
import pytest
from pathlib import Path

from scripts.librarian.index_monitor import IndexMonitor


class TestMeasureIndex:
    """Tests for measure_index."""

    def test_measure_valid_json_index(self, tmp_path):
        """Measure a small valid JSON index file."""
        index_path = tmp_path / "symbols.json"
        data = {
            "generated": "2025-01-01",
            "symbols": {
                "func_a": [{"file": "a.py", "line": 1, "type": "function", "signature": "def func_a()"}],
                "func_b": [{"file": "b.py", "line": 1, "type": "function", "signature": "def func_b()"}],
            },
        }
        index_path.write_text(json.dumps(data))

        monitor = IndexMonitor(tmp_path)
        metrics = monitor.measure_index(index_path)
        assert metrics.size_bytes > 0
        assert metrics.entry_count == 2  # 2 symbol entries
        assert metrics.load_time_ms >= 0

    def test_measure_files_index(self, tmp_path):
        """JSON with 'files' key counts entries via len(files)."""
        index_path = tmp_path / "metrics.json"
        data = {"files": {"a.py": {}, "b.py": {}, "c.py": {}}}
        index_path.write_text(json.dumps(data))

        monitor = IndexMonitor(tmp_path)
        metrics = monitor.measure_index(index_path)
        assert metrics.entry_count == 3

    def test_measure_nonexistent_raises(self, tmp_path):
        """FileNotFoundError for missing file."""
        monitor = IndexMonitor(tmp_path)
        with pytest.raises(FileNotFoundError):
            monitor.measure_index(tmp_path / "missing.json")

    def test_measure_corrupted_json_raises(self, tmp_path):
        """Invalid JSON raises JSONDecodeError."""
        index_path = tmp_path / "bad.json"
        index_path.write_text("{not valid json")

        monitor = IndexMonitor(tmp_path)
        with pytest.raises(json.JSONDecodeError):
            monitor.measure_index(index_path)

    def test_avg_entry_size_calculated(self, tmp_path):
        """avg_entry_size is size_bytes / entry_count."""
        index_path = tmp_path / "index.json"
        data = {"symbols": {"a": [{"file": "a.py"}]}}
        index_path.write_text(json.dumps(data))

        monitor = IndexMonitor(tmp_path)
        metrics = monitor.measure_index(index_path)
        assert metrics.avg_entry_size == metrics.size_bytes // metrics.entry_count


class TestCheckIndex:
    """Tests for check_index."""

    def test_small_index_ok(self, tmp_path):
        """Small index returns status 'ok'."""
        index_path = tmp_path / "small.json"
        index_path.write_text(json.dumps({"symbols": {"a": []}}))

        monitor = IndexMonitor(tmp_path)
        status, _warnings = monitor.check_index(index_path)
        assert status == "ok"

    def test_missing_file_returns_error(self, tmp_path):
        """Non-existent file returns error status."""
        monitor = IndexMonitor(tmp_path)
        status, warnings = monitor.check_index(tmp_path / "missing.json")
        assert status == "error"
        assert len(warnings) > 0

    def test_corrupted_json_returns_error(self, tmp_path):
        """Corrupted JSON returns error status."""
        index_path = tmp_path / "bad.json"
        index_path.write_text("not json")

        monitor = IndexMonitor(tmp_path)
        status, _warnings = monitor.check_index(index_path)
        assert status == "error"


class TestCheckAllIndexes:
    """Tests for check_all_indexes."""

    def test_all_missing_returns_missing(self, tmp_path):
        """No index files results in all 'missing' statuses."""
        monitor = IndexMonitor(tmp_path)
        results = monitor.check_all_indexes()
        for _filename, result in results["indexes"].items():
            assert result["status"] == "missing"

    def test_mixed_statuses(self, tmp_path):
        """Some present and some missing indexes."""
        # Create just symbols.json
        (tmp_path / "symbols.json").write_text(json.dumps({"symbols": {}}))

        monitor = IndexMonitor(tmp_path)
        results = monitor.check_all_indexes()
        assert results["indexes"]["symbols.json"]["status"] == "ok"
        assert results["indexes"]["links.json"]["status"] == "missing"

    def test_returns_overall_status(self, tmp_path):
        """Overall status is the maximum severity."""
        monitor = IndexMonitor(tmp_path)
        results = monitor.check_all_indexes()
        assert "overall_status" in results
        assert results["overall_status"] in ("ok", "warning", "error", "critical")


class TestGetReport:
    """Tests for get_report."""

    def test_report_is_string(self, tmp_path):
        """Returns a formatted string."""
        monitor = IndexMonitor(tmp_path)
        report = monitor.get_report()
        assert isinstance(report, str)

    def test_report_includes_header(self, tmp_path):
        """Report contains the INDEX HEALTH REPORT header."""
        monitor = IndexMonitor(tmp_path)
        report = monitor.get_report()
        assert "INDEX HEALTH REPORT" in report

    def test_report_includes_status(self, tmp_path):
        """Report shows overall status."""
        monitor = IndexMonitor(tmp_path)
        report = monitor.get_report()
        assert "Overall Status:" in report


class TestLogToFile:
    """Tests for log_to_file."""

    def test_log_creates_file(self, tmp_path):
        """log_to_file writes a report file."""
        monitor = IndexMonitor(tmp_path)
        output = tmp_path / "health.log"
        monitor.log_to_file(output)
        assert output.exists()
        content = output.read_text()
        assert "INDEX HEALTH REPORT" in content
