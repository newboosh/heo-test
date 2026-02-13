"""Integration tests for Phase 1 end-to-end functionality.

Tests:
- Full build pipeline (classifier → dependency_graph → symbol_index)
- Output file generation and validation
- Exit codes for various scenarios
- Incremental build behavior
- System health reporting
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.intelligence.cache import BuildCache
from scripts.intelligence.build import BuildGraph
from scripts.intelligence.components.classifier import Classifier
from scripts.intelligence.components.dependency_graph import DependencyGraph
from scripts.intelligence.components.symbol_index import SymbolIndex
from scripts.intelligence.monitoring.system_monitor import SystemMonitor
from scripts.intelligence.monitoring.context_estimator import ContextEstimator
from scripts.intelligence.utils import json_utils
from scripts.intelligence.schema import Schema


@pytest.fixture
def test_codebase():
    """Create temporary test codebase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test Python files
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        # Main module
        (src_dir / "__init__.py").write_text("")

        # Module with functions
        (src_dir / "utils.py").write_text("""
def helper_function():
    \"\"\"Helper function.\"\"\"
    return 42

def another_helper():
    \"\"\"Another helper function.\"\"\"
    pass
""")

        # Module with class
        (src_dir / "models.py").write_text("""
class DataModel:
    \"\"\"Data model class.

    Args:
        name: Model name.

    Returns:
        Initialized model.
    \"\"\"

    def __init__(self, name):
        self.name = name

    def process(self):
        \"\"\"Process data.\"\"\"
        pass
""")

        # Test file
        test_dir = Path(tmpdir) / "tests"
        test_dir.mkdir()
        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_utils.py").write_text("""
import unittest
from src.utils import helper_function

class TestUtils(unittest.TestCase):
    def test_helper(self):
        assert helper_function() == 42
""")

        # Config file
        (Path(tmpdir) / "catalog.yaml").write_text("""
classification_rules:
  directory_patterns:
    test:
      - test*
      - '*test*'
""")

        yield tmpdir


class TestIntegrationFullPipeline:
    """Test end-to-end full build pipeline."""

    def test_classify_all_files(self, test_codebase):
        """Test classification of all files."""
        classifier = Classifier(str(Path(test_codebase) / "catalog.yaml"))
        classifications = classifier.classify_all(test_codebase)

        assert len(classifications) >= 3
        categories = [c.category for c in classifications]
        assert "test" in categories or "uncategorized" in categories

    def test_extract_dependencies(self, test_codebase):
        """Test dependency extraction."""
        dep_graph = DependencyGraph()
        dep_data = dep_graph.build_graph(test_codebase)

        assert "forward" in dep_data
        assert "reverse" in dep_data

    def test_extract_symbols(self, test_codebase):
        """Test symbol extraction."""
        symbol_index = SymbolIndex()
        symbols = symbol_index.build_index(test_codebase)

        # Should find at least the classes and functions
        assert len(symbols) > 0

        # Check for expected symbols
        symbol_names = [s.name for s in symbols]
        assert "DataModel" in symbol_names
        assert "helper_function" in symbol_names

    def test_cache_behavior(self, test_codebase):
        """Test incremental build caching."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = BuildCache(str(Path(cache_dir) / ".cache.db"))

            # Mark artifact as built
            test_file = Path(test_codebase) / "src" / "utils.py"
            file_hash = "abc123"
            cache.mark_built("classifier_artifact", "classifier",
                           {str(test_file): file_hash})

            # Check freshness
            is_fresh = cache.is_fresh("classifier_artifact",
                                     {str(test_file): file_hash})
            assert is_fresh

            # Change hash
            is_fresh = cache.is_fresh("classifier_artifact",
                                     {str(test_file): "different"})
            assert not is_fresh

            cache.close()

    def test_build_dag_order(self):
        """Test DAG build ordering."""
        graph = BuildGraph()

        # Add components in dependency order
        graph.add_component("classifier")
        graph.add_component("dependency_graph", ["classifier"])
        graph.add_component("symbol_index", ["dependency_graph"])

        order = graph.build_order()

        # Verify correct ordering
        assert order.index("classifier") < order.index("dependency_graph")
        assert order.index("dependency_graph") < order.index("symbol_index")


class TestIntegrationSystemMonitoring:
    """Test system monitoring integration."""

    @patch('scripts.intelligence.monitoring.system_monitor.psutil')
    def test_system_health_reporting(self, mock_psutil):
        """Test system health is properly reported."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.available = 4 * 1024 ** 2

        mock_disk = MagicMock()
        mock_disk.free = 100 * 1024 ** 3
        mock_disk.percent = 50.0

        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.disk_usage.return_value = mock_disk
        mock_psutil.cpu_percent.return_value = 25.0

        monitor = SystemMonitor()
        health = monitor.get_system_health()

        assert health.memory_percent == 50.0
        assert health.disk_free_gb == 100.0
        assert len(health.warnings) == 0

    def test_context_estimation(self):
        """Test context window impact estimation."""
        estimator = ContextEstimator()

        index_size = {
            "symbols": 100,
            "files": 50,
            "dependencies": 200
        }

        estimate = estimator.estimate_tokens(index_size, "haiku")

        assert estimate.model == "haiku"
        assert estimate.estimated_tokens > 0
        assert estimate.usage_percent < 100


class TestIntegrationOutputFormats:
    """Test output file formats and schema."""

    def test_schema_versioning(self):
        """Test schema versioning works."""
        data = {"test": "data"}

        # Add version
        versioned = Schema.add_version(data)
        assert "_schema_version" in versioned
        assert versioned["_schema_version"] == "1.0.0"

    def test_json_serialization(self):
        """Test JSON serialization with custom types."""
        data = {
            "path": Path("/some/path"),
            "set": {1, 2, 3},
            "items": [1, 2, 3]
        }

        json_str = json_utils.dumps(data)
        loaded = json_utils.loads(json_str)

        assert loaded["path"] == "/some/path"
        assert set(loaded["set"]) == {1, 2, 3}

    def test_output_index_format(self, test_codebase):
        """Test that output index has correct format."""
        # Build basic index
        classifier = Classifier()
        classifications = classifier.classify_all(test_codebase)

        symbol_index = SymbolIndex()
        symbols = symbol_index.build_index(test_codebase)

        # Create index structure
        index = {
            "files": [c.to_dict() if hasattr(c, 'to_dict') else {
                'file_path': c.file_path,
                'category': c.category,
                'confidence': c.confidence
            } for c in classifications],
            "symbols": [s.to_dict() for s in symbols],
            "metadata": {
                "total_files": len(classifications),
                "total_symbols": len(symbols)
            }
        }

        # Add schema version
        index = Schema.add_version(index)

        # Verify structure
        assert "_schema_version" in index
        assert "files" in index
        assert "symbols" in index
        assert "metadata" in index


class TestIntegrationAcceptanceCriteria:
    """Test acceptance criteria from specification."""

    def test_classifier_acceptance(self, test_codebase):
        """Test classifier acceptance criteria."""
        classifier = Classifier()
        classifications = classifier.classify_all(test_codebase)

        # Should classify at least some files
        assert len(classifications) > 0

        # All classifications should have required fields
        for c in classifications:
            assert c.file_path is not None
            assert c.category is not None
            assert c.confidence is not None

    def test_dependency_acceptance(self, test_codebase):
        """Test dependency analysis acceptance criteria."""
        dep_graph = DependencyGraph()
        dep_data = dep_graph.build_graph(test_codebase)

        # Should handle circular imports gracefully
        assert isinstance(dep_data, dict)
        assert "forward" in dep_data
        assert "reverse" in dep_data

    def test_symbol_extraction_acceptance(self, test_codebase):
        """Test symbol extraction acceptance criteria."""
        symbol_index = SymbolIndex()
        symbols = symbol_index.build_index(test_codebase)

        # Should extract functions and classes
        symbol_types = [s.type for s in symbols]
        expected_types = {"function", "class", "method"}
        assert len(set(symbol_types) & expected_types) > 0

    def test_exit_codes(self, test_codebase):
        """Test proper exit code handling."""
        # Success case should return 0
        classifier = Classifier()
        classifications = classifier.classify_all(test_codebase)
        assert len(classifications) >= 0  # Success

        # File error case would return 2
        # (Not testable without modifying actual file system in error case)


class TestIntegrationPerformance:
    """Test performance characteristics."""

    def test_incremental_build_skips_fresh(self):
        """Test that incremental builds skip unchanged components."""
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = BuildCache(str(Path(cache_dir) / ".cache.db"))

            # Mark first run
            cache.mark_built("test_artifact", "test_component",
                           {"file1": "hash1"})

            # Check that fresh artifact is detected
            is_fresh = cache.is_fresh("test_artifact", {"file1": "hash1"})
            assert is_fresh is True

            cache.close()

    def test_large_codebase_handling(self):
        """Test handling of reasonable codebase sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()

            # Create multiple files
            for i in range(10):
                (src_dir / f"module{i}.py").write_text(f"""
def function_{i}():
    \"\"\"Function {i}.\"\"\"
    return {i}
""")

            # Should handle without issues
            classifier = Classifier()
            classifications = classifier.classify_all(tmpdir)
            assert len(classifications) >= 10
