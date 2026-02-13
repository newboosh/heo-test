"""Phase 2 tests - semantic layer components.

Tests for:
- Metrics (complexity, coupling)
- Importance scoring
- Content profiling

Note: TestMapper is tested via integration tests in test_phase3_integration.py
"""

import pytest
import tempfile
import textwrap
from pathlib import Path

from scripts.intelligence.components.metrics import MetricsAnalyzer, Metrics
from scripts.intelligence.components.importance_scorer import ImportanceScorer
from scripts.intelligence.components.content_profiler import ContentProfiler
from scripts.intelligence.components.symbol_index import Symbol, SymbolIndex


@pytest.fixture
def test_codebase():
    """Create test codebase with symbols and tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Source module
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()

        (src_dir / "calculator.py").write_text(textwrap.dedent("""\
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

def complex_function(x):
    \"\"\"Complex function with multiple branches.\"\"\"
    if x > 0:
        if x > 10:
            return x * 2
        else:
            return x + 1
    else:
        return -x
"""))

        (src_dir / "models.py").write_text(textwrap.dedent("""\
class DataModel:
    \"\"\"Data model class.\"\"\"

    def __init__(self, name):
        self.name = name

    def process(self):
        \"\"\"Process data.\"\"\"
        pass

    def validate(self):
        \"\"\"Validate data.\"\"\"
        if not self.name:
            raise ValueError("Name required")
        return True
"""))

        # Test module
        test_dir = Path(tmpdir) / "tests"
        test_dir.mkdir()

        (test_dir / "test_calculator.py").write_text(textwrap.dedent("""\
def test_add():
    \"\"\"Test add function.\"\"\"
    from src.calculator import add
    assert add(2, 3) == 5

def test_add_negative():
    \"\"\"Test add with negative numbers.\"\"\"
    from src.calculator import add
    assert add(-1, 1) == 0
"""))

        (test_dir / "test_models.py").write_text(textwrap.dedent("""\
def test_data_model():
    \"\"\"Test DataModel class.\"\"\"
    from src.models import DataModel
    model = DataModel("test")
    assert model.name == "test"

def test_validate():
    \"\"\"Test validation.\"\"\"
    from src.models import DataModel
    model = DataModel("test")
    assert model.validate()
"""))

        yield tmpdir


class TestMetricsAnalyzer:
    """Test complexity and coupling metrics."""

    def test_function_complexity(self, test_codebase):
        """Test function complexity calculation."""
        analyzer = MetricsAnalyzer()
        calc_file = Path(test_codebase) / "src" / "calculator.py"

        metrics = analyzer.analyze_file(str(calc_file))

        # add should have low complexity
        assert "add" in metrics
        assert metrics["add"].complexity == 1

        # complex_function should have higher complexity (multiple if/else)
        assert "complex_function" in metrics
        assert metrics["complex_function"].complexity > 2

    def test_class_metrics(self, test_codebase):
        """Test class metrics."""
        analyzer = MetricsAnalyzer()
        models_file = Path(test_codebase) / "src" / "models.py"

        metrics = analyzer.analyze_file(str(models_file))

        assert "DataModel" in metrics
        metric = metrics["DataModel"]
        assert metric.type == "class"
        assert metric.methods == 3  # __init__, process, validate


class TestImportanceScorer:
    """Test importance scoring.

    Verifies that:
    - Computed values (percentiles, counts) are numbers
    - Agent decisions (factor levels) are words
    """

    def test_score_uses_words_for_factors(self):
        """Test that factor assessments use words, not numbers."""
        scorer = ImportanceScorer()

        metrics = {
            "add": Metrics(name="add", file="calc.py", type="function",
                         loc=2, complexity=1, coupling=0),
            "complex_function": Metrics(name="complex_function", file="calc.py",
                                       type="function", loc=10, complexity=8,
                                       coupling=2),
            "DataModel": Metrics(name="DataModel", file="models.py",
                                type="class", loc=20, complexity=3,
                                coupling=1, methods=3)
        }

        test_coverage = {"add": 2, "complex_function": 0, "DataModel": 1}
        coupling_graph = {"add": set(), "complex_function": {"add"},
                         "DataModel": set()}

        scores = scorer.score_symbols(metrics, test_coverage, coupling_graph, 3)

        assert len(scores) == 3

        # Verify factors use words (none/low/medium/high/critical)
        valid_levels = {"none", "low", "medium", "high", "critical"}
        for score in scores:
            for factor_name, factor_level in score.factors.items():
                assert factor_level in valid_levels, \
                    f"Factor {factor_name} should use words, got: {factor_level}"

        # Verify raw_metrics contain computed numbers
        for score in scores:
            assert isinstance(score.raw_metrics["test_count"], int)
            assert isinstance(score.raw_metrics["complexity"], int)
            assert isinstance(score.raw_metrics["dependents"], int)

        # Verify overall level uses words
        for score in scores:
            assert score.level in valid_levels

    def test_percentile_is_computed_number(self):
        """Test percentile is a computed number, not a word."""
        scorer = ImportanceScorer()

        metrics = {
            "low": Metrics(name="low", file="f.py", type="function",
                          loc=1, complexity=1, coupling=0),
            "medium": Metrics(name="medium", file="f.py", type="function",
                             loc=5, complexity=5, coupling=1),
            "high": Metrics(name="high", file="f.py", type="function",
                           loc=20, complexity=10, coupling=5)
        }

        test_coverage = {}
        coupling_graph = {k: set() for k in metrics.keys()}

        scores = scorer.score_symbols(metrics, test_coverage, coupling_graph, 3)

        # Percentiles are computed numbers (0-100)
        assert all(isinstance(s.percentile, float) for s in scores)
        assert all(0 <= s.percentile <= 100 for s in scores)

        # Higher raw metrics should yield higher percentile
        high = next(s for s in scores if s.name == "high")
        low = next(s for s in scores if s.name == "low")
        assert high.percentile > low.percentile

        # Level property converts percentile to word
        assert high.level in {"high", "critical"}
        assert low.level in {"none", "low"}


class TestContentProfiler:
    """Test semantic summarization."""

    def test_keyword_extraction(self):
        """Test keyword extraction from symbol names."""
        indexer = ContentProfiler()

        symbols = [
            Symbol(name="calculate_sum", file="f.py", line=1, type="function"),
            Symbol(name="DataValidationError", file="f.py", line=10, type="class"),
        ]

        entries = indexer.index_symbols(symbols, {})

        assert len(entries) == 2

        # Check keywords are extracted
        calc_entry = entries[0]
        assert "sum" in calc_entry.keywords or "calculate" in calc_entry.keywords

    def test_categorization(self):
        """Test symbol categorization."""
        indexer = ContentProfiler()

        symbols = [
            Symbol(name="get_name", file="f.py", line=1, type="function"),
            Symbol(name="UserModel", file="f.py", line=10, type="class"),
            Symbol(name="test_validation", file="f.py", line=20, type="function"),
        ]

        metrics = {
            "get_name": Metrics(name="get_name", file="f.py", type="function",
                               loc=3, complexity=1, coupling=0),
            "UserModel": Metrics(name="UserModel", file="f.py", type="class",
                                loc=30, complexity=5, coupling=2),
            "test_validation": Metrics(name="test_validation", file="f.py",
                                      type="function", loc=5, complexity=1,
                                      coupling=0),
        }

        entries = indexer.index_symbols(symbols, metrics)

        # Check categories
        getter = next(e for e in entries if e.name == "get_name")
        assert "accessor" in getter.categories

        tester = next(e for e in entries if e.name == "test_validation")
        assert "test" in tester.categories

    def test_search(self):
        """Test content profile search."""
        indexer = ContentProfiler()

        symbols = [
            Symbol(name="calculate_total", file="f.py", line=1,
                  type="function", docstring="Calculate total sum"),
            Symbol(name="validate_input", file="f.py", line=10,
                  type="function", docstring="Validate user input"),
        ]

        indexer.index_symbols(symbols, {})

        # Search for keyword
        results = indexer.search("calculate")
        assert len(results) >= 1
        assert any("calculate" in r.name for r in results)

        # Search in docstring
        results = indexer.search("sum")
        assert len(results) >= 1


class TestIntegrationPhase2:
    """Integration tests for Phase 2 components."""

    def test_full_analysis_pipeline(self, test_codebase):
        """Test full Phase 2 analysis pipeline."""
        # Extract symbols
        symbol_index = SymbolIndex()
        src_dir = Path(test_codebase) / "src"
        symbols = symbol_index.extract_symbols(str(src_dir / "calculator.py"))

        # Analyze metrics
        analyzer = MetricsAnalyzer()
        metrics = analyzer.analyze_file(str(src_dir / "calculator.py"))

        # Score importance
        scorer = ImportanceScorer()
        scores = scorer.score_symbols(metrics, {}, {}, len(symbols))

        # Generate content profiles
        indexer = ContentProfiler()
        profiles = indexer.index_symbols(symbols, metrics)

        # Verify all stages work
        assert len(symbols) > 0
        assert len(metrics) > 0
        assert len(scores) > 0
        assert len(profiles) > 0

        # Check relationships
        for symbol in symbols:
            assert symbol.name in metrics or symbol.type == "method"
