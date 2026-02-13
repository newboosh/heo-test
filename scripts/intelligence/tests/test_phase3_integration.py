"""End-to-end integration tests for Phase 3 (Integration & Verification).

Tests for:
- Full pipeline with docstring linting
- Performance validation
- Real codebase testing
"""

import pytest
import tempfile
import time
from pathlib import Path

from scripts.intelligence.components.symbol_index import SymbolIndex
from scripts.intelligence.components.metrics import MetricsAnalyzer
from scripts.intelligence.components.importance_scorer import ImportanceScorer
from scripts.intelligence.components.content_profiler import ContentProfiler
from scripts.intelligence.components.docstring_linter import DocstringLinter
from scripts.intelligence.monitoring.system_monitor import SystemMonitor
from scripts.intelligence.monitoring.context_estimator import ContextEstimator


class TestFullPipelineWithLinting:
    """Test complete Phase 1-3 pipeline including docstring linting."""

    @pytest.fixture
    def well_documented_codebase(self):
        """Create codebase with good docstrings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()

            (src_dir / "calculator.py").write_text('''
"""Calculator module for arithmetic operations."""

def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Sum of a and b.
    """
    return a + b

def divide(a: int, b: int) -> float:
    """Divide two numbers with error handling.

    Args:
        a: Numerator.
        b: Denominator.

    Returns:
        Result of division.

    Raises:
        ZeroDivisionError: When b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b

class Calculator:
    """Basic calculator with operation tracking.

    Attributes:
        operations: Count of operations performed.
        history: List of recent results.
    """

    def __init__(self):
        """Initialize calculator with empty history."""
        self.operations = 0
        self.history = []

    def compute(self, a: int, b: int, op: str) -> int:
        """Perform arithmetic operation.

        Args:
            a: First operand.
            b: Second operand.
            op: Operation (add, sub, mul, div).

        Returns:
            Result of the operation.

        Raises:
            ValueError: When operation is not supported.
        """
        if op == "add":
            result = add(a, b)
        elif op == "sub":
            result = a - b
        else:
            raise ValueError(f"Unsupported operation: {op}")

        self.operations += 1
        self.history.append(result)
        return result
''')

            yield str(src_dir / "calculator.py")

    def test_symbols_extracted(self, well_documented_codebase):
        """Test that all symbols are extracted."""
        indexer = SymbolIndex()
        symbols = indexer.extract_symbols(well_documented_codebase)

        # Should find module, functions, and class
        names = {s.name for s in symbols}
        assert 'add' in names
        assert 'divide' in names
        assert 'Calculator' in names
        assert 'compute' in names

    def test_metrics_calculated(self, well_documented_codebase):
        """Test that metrics are calculated correctly."""
        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(well_documented_codebase)

        # Should have metrics for module, functions, and class
        assert 'add' in metrics
        assert 'divide' in metrics
        assert 'Calculator' in metrics
        # Note: compute is a method of Calculator, not a top-level symbol

        # Divide should have higher complexity (has if statement and raise)
        assert metrics['divide'].complexity > metrics['add'].complexity

    def test_importance_scores(self, well_documented_codebase):
        """Test importance scoring."""
        indexer = SymbolIndex()
        symbols = indexer.extract_symbols(well_documented_codebase)

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(well_documented_codebase)

        scorer = ImportanceScorer()
        scores = scorer.score_symbols(metrics, {}, {}, len(symbols))

        # Should have scores for all symbols
        assert len(scores) >= 3
        # Percentiles are computed numbers (0-100)
        assert all(0 <= s.percentile <= 100 for s in scores)
        # Factors use words (none/low/medium/high/critical)
        valid_levels = {"none", "low", "medium", "high", "critical"}
        assert all(s.level in valid_levels for s in scores)

        # Class should have higher importance than simple function
        calc_score = next((s for s in scores if s.name == 'Calculator'), None)
        add_score = next((s for s in scores if s.name == 'add'), None)

        if calc_score and add_score:
            assert calc_score.percentile >= add_score.percentile

    def test_content_profiling(self, well_documented_codebase):
        """Test content profile generation."""
        indexer = SymbolIndex()
        symbols = indexer.extract_symbols(well_documented_codebase)

        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(well_documented_codebase)

        profiler = ContentProfiler()
        profiles = profiler.index_symbols(symbols, metrics)

        # Should have entries for all symbols
        assert len(profiles) >= 3

        # Check searchability
        calc_results = profiler.search("calculator")
        assert len(calc_results) >= 1

    def test_docstring_linting(self, well_documented_codebase):
        """Test that docstring linter validates documented code."""
        linter = DocstringLinter()
        issues = linter.lint_file(well_documented_codebase)

        # Well-documented code should have minimal issues
        # (may have some style warnings, but no missing docstrings)
        missing_issues = [i for i in issues if i.issue_type == 'missing']
        assert len(missing_issues) == 0

    def test_full_pipeline_integration(self, well_documented_codebase):
        """Test complete Phase 1-3 pipeline."""
        # Phase 1: Extract symbols
        symbol_indexer = SymbolIndex()
        symbols = symbol_indexer.extract_symbols(well_documented_codebase)
        assert len(symbols) >= 3

        # Phase 2: Analyze metrics
        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(well_documented_codebase)
        assert len(metrics) >= 3

        # Phase 2: Score importance
        scorer = ImportanceScorer()
        scores = scorer.score_symbols(metrics, {}, {}, len(symbols))
        assert len(scores) >= 3

        # Phase 2: Generate content profiles
        profiler = ContentProfiler()
        profiles = profiler.index_symbols(symbols, metrics)
        assert len(profiles) >= 3

        # Phase 3: Lint docstrings
        linter = DocstringLinter()
        lint_issues = linter.lint_file(well_documented_codebase)
        assert isinstance(lint_issues, list)

        # Verify enriched index structure
        enriched_index = {
            'symbols': len(symbols),
            'metrics': len(metrics),
            'scores': len(scores),
            'profiles': len(profiles),
            'lint_issues': len(lint_issues),
        }
        assert enriched_index['symbols'] > 0
        assert enriched_index['metrics'] > 0
        assert enriched_index['scores'] > 0
        assert enriched_index['profiles'] > 0


class TestDocstringLintingReal:
    """Test docstring linting on real code patterns."""

    def test_lint_mixed_quality_code(self):
        """Test linting code with mixed documentation quality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "mixed.py"
            test_file.write_text('''
"""Module with mixed docstring quality."""

def well_documented(x: int) -> int:
    """Square a number.

    Args:
        x: The number to square.

    Returns:
        The square of x.
    """
    return x * x

def poorly_documented(y):
    return y + 1

class WellDocumentedClass:
    """A well-documented class.

    Attributes:
        value: The stored value.
    """
    def __init__(self, value):
        """Initialize with value."""
        self.value = value

class PartiallyDocumentedClass:
    """A class with only class docstring."""
    def __init__(self, value):
        self.value = value
''')

            linter = DocstringLinter()
            issues = linter.lint_file(str(test_file))

            # Should find issues with poorly_documented and __init__
            assert len(issues) > 0

            # Should have errors for missing docstrings
            errors = [i for i in issues if i.severity == 'error']
            assert len(errors) >= 1

    def test_lint_summary_contains_suggestions(self):
        """Test that lint summary provides actionable suggestions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def no_docstring(a, b):
    return a + b
''')

            linter = DocstringLinter()
            issues = linter.lint_file(str(test_file))

            assert len(issues) > 0
            for issue in issues:
                assert len(issue.suggestion) > 0
                assert 'docstring' in issue.suggestion.lower() or \
                       'Args' in issue.suggestion or \
                       'Returns' in issue.suggestion


class TestPerformanceValidation:
    """Test performance characteristics of Phase 3 components."""

    def test_docstring_linting_performance(self):
        """Test that docstring linting is fast even on large files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a large file with many functions
            test_file = Path(tmpdir) / "large.py"
            functions = []
            for i in range(100):
                functions.append(f'''
def function_{i}(x: int) -> int:
    """Function {i}."""
    return x + {i}
''')
            test_file.write_text('\n'.join(functions))

            linter = DocstringLinter()
            start = time.time()
            _issues = linter.lint_file(str(test_file))
            elapsed = time.time() - start

            # Should complete in reasonable time (< 1 second)
            assert elapsed < 1.0
            assert _issues is not None  # Verify linting produced output

    def test_content_profiling_performance(self):
        """Test that content profiling is fast."""
        from scripts.intelligence.components.symbol_index import Symbol
        from scripts.intelligence.components.metrics import Metrics

        # Create many symbols
        symbols = [
            Symbol(
                name=f"symbol_{i}",
                file="test.py",
                line=i,
                type="function",
                docstring=f"Symbol {i} description"
            )
            for i in range(500)
        ]

        metrics = {
            f"symbol_{i}": Metrics(
                name=f"symbol_{i}",
                file="test.py",
                type="function",
                loc=10 + i,
                complexity=1 + (i % 5),
                coupling=i % 3
            )
            for i in range(500)
        }

        profiler = ContentProfiler()
        start = time.time()
        profiles = profiler.index_symbols(symbols, metrics)
        elapsed = time.time() - start

        assert len(profiles) == 500
        # Should complete in reasonable time (< 2 seconds)
        assert elapsed < 2.0


class TestSystemHealth:
    """Test system health monitoring for Phase 3."""

    def test_system_monitor_availability(self):
        """Test that system monitor works."""
        monitor = SystemMonitor()
        health = monitor.get_system_health()

        # health is a SystemHealth dataclass
        assert hasattr(health, 'memory_percent')
        assert hasattr(health, 'disk_free_gb')
        assert hasattr(health, 'cpu_percent')
        assert hasattr(health, 'warnings')
        assert 0 <= health.memory_percent <= 100
        assert health.disk_free_gb > 0

    def test_context_estimator_for_index(self):
        """Test context window estimation for generated indexes."""
        estimator = ContextEstimator()

        # Create a typical index size estimate
        index_size = {
            'symbols': 5000,
            'files': 500,
            'dependencies': 2000,
        }

        for model in ['haiku', 'sonnet', 'opus']:
            estimate = estimator.estimate_tokens(index_size, model)
            assert estimate.estimated_tokens > 0
            assert estimate.usage_percent > 0  # Can be >100 for large indexes
            assert estimate.model == model

        # Haiku and Opus should have different usage percentages
        haiku_estimate = estimator.estimate_tokens(index_size, 'haiku')
        opus_estimate = estimator.estimate_tokens(index_size, 'opus')
        # Same token count but different budgets = different percentages
        assert haiku_estimate.estimated_tokens == opus_estimate.estimated_tokens
        # Haiku has smaller budget, so higher percentage
        assert haiku_estimate.usage_percent > opus_estimate.usage_percent

        # Should recommend model based on size
        recommendation = estimator.recommend_model(index_size)
        assert recommendation in ['haiku', 'sonnet', 'opus']
