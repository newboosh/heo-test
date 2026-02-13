"""Tests for the importance scorer module."""

import pytest

from scripts.librarian.importance_scorer import ImportanceScorer, ImportanceMetrics


class TestImportanceScorer:
    """Tests for core scoring functionality."""

    def test_add_and_compute_single_metric(self):
        """Add one metric and compute importance."""
        scorer = ImportanceScorer()
        scorer.add_metric("func_a", ImportanceMetrics(imported_by_count=5, test_count=3))
        result = scorer.compute_importance("func_a")
        assert "score" in result
        assert isinstance(result["score"], float)

    def test_score_range_0_to_1(self):
        """Score is always in [0, 1]."""
        scorer = ImportanceScorer()
        for i in range(10):
            scorer.add_metric(f"sym_{i}", ImportanceMetrics(
                imported_by_count=i * 5,
                test_count=i,
                cyclomatic_complexity=i + 1,
            ))
        for sym_id in scorer.metrics_cache:
            result = scorer.compute_importance(sym_id)
            assert 0.0 <= result["score"] <= 1.0

    def test_high_centrality_produces_high_score(self):
        """Symbol imported by many gets a higher score."""
        scorer = ImportanceScorer()
        scorer.add_metric("popular", ImportanceMetrics(imported_by_count=100))
        scorer.add_metric("obscure", ImportanceMetrics(imported_by_count=0))
        pop = scorer.compute_importance("popular")
        obs = scorer.compute_importance("obscure")
        assert pop["score"] > obs["score"]

    def test_exported_symbol_gets_api_bonus(self):
        """is_exported=True adds the api_surface component."""
        scorer = ImportanceScorer()
        scorer.add_metric("public", ImportanceMetrics(is_exported=True))
        scorer.add_metric("private", ImportanceMetrics(is_exported=False))
        pub = scorer.compute_importance("public")
        priv = scorer.compute_importance("private")
        assert pub["components"]["api_surface"] == 0.10
        assert priv["components"]["api_surface"] == 0

    def test_well_documented_gets_doc_score(self):
        """has_docstring=True contributes to documentation component."""
        scorer = ImportanceScorer()
        scorer.add_metric("documented", ImportanceMetrics(
            has_docstring=True, docstring_quality=0.8,
        ))
        scorer.add_metric("undocumented", ImportanceMetrics(
            has_docstring=False, docstring_quality=0.0,
        ))
        doc_result = scorer.compute_importance("documented")
        undoc_result = scorer.compute_importance("undocumented")
        assert doc_result["components"]["documentation"] > undoc_result["components"]["documentation"]

    def test_unknown_symbol_returns_error(self):
        """Symbol not in cache returns error dict."""
        scorer = ImportanceScorer()
        result = scorer.compute_importance("nonexistent")
        assert result["score"] == 0.0
        assert "error" in result

    def test_score_components_present(self):
        """Result includes all expected component keys."""
        scorer = ImportanceScorer()
        scorer.add_metric("sym", ImportanceMetrics(imported_by_count=3))
        result = scorer.compute_importance("sym")
        assert "centrality" in result["components"]
        assert "documentation" in result["components"]
        assert "test_coverage" in result["components"]
        assert "complexity" in result["components"]
        assert "api_surface" in result["components"]


class TestPercentileThresholds:
    """Tests for percentile threshold computation."""

    def test_compute_with_multiple_symbols(self):
        """Thresholds make sense with multiple symbols."""
        scorer = ImportanceScorer()
        for i in range(20):
            scorer.add_metric(f"sym_{i}", ImportanceMetrics(
                imported_by_count=i * 2,
                cyclomatic_complexity=i + 1,
                test_count=i,
            ))
        thresholds = scorer.compute_percentile_thresholds()
        assert "imported_by" in thresholds
        assert thresholds["imported_by"]["p25"] <= thresholds["imported_by"]["p50"]
        assert thresholds["imported_by"]["p50"] <= thresholds["imported_by"]["p75"]

    def test_single_symbol_fallback(self):
        """Single symbol (< 2 data points) uses fallback path."""
        scorer = ImportanceScorer()
        scorer.add_metric("only", ImportanceMetrics(imported_by_count=10))
        thresholds = scorer.compute_percentile_thresholds()
        assert thresholds["imported_by"]["p25"] == 10
        assert thresholds["imported_by"]["p90"] == 10

    def test_empty_cache_returns_empty(self):
        """No metrics returns empty thresholds."""
        scorer = ImportanceScorer()
        thresholds = scorer.compute_percentile_thresholds()
        assert thresholds == {}

    def test_threshold_invalidation_on_add(self):
        """Adding new metric invalidates cached thresholds."""
        scorer = ImportanceScorer()
        scorer.add_metric("a", ImportanceMetrics(imported_by_count=5))
        scorer.compute_importance("a")  # Triggers threshold computation
        assert scorer._percentile_thresholds is not None

        scorer.add_metric("b", ImportanceMetrics(imported_by_count=10))
        assert scorer._percentile_thresholds is None  # Invalidated


class TestGetRankedSymbols:
    """Tests for get_ranked_symbols."""

    def test_ranked_in_descending_order(self):
        """Symbols are sorted by score descending."""
        scorer = ImportanceScorer()
        scorer.add_metric("low", ImportanceMetrics(imported_by_count=0))
        scorer.add_metric("high", ImportanceMetrics(
            imported_by_count=50, is_exported=True, has_docstring=True,
        ))
        scorer.add_metric("mid", ImportanceMetrics(imported_by_count=10))
        ranked = scorer.get_ranked_symbols()
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_limit_parameter(self):
        """limit=N returns at most N symbols."""
        scorer = ImportanceScorer()
        for i in range(20):
            scorer.add_metric(f"sym_{i}", ImportanceMetrics(imported_by_count=i))
        ranked = scorer.get_ranked_symbols(limit=5)
        assert len(ranked) == 5


class TestExportMetricsSummary:
    """Tests for export_metrics_summary."""

    def test_summary_includes_distribution(self):
        """Summary has high/medium/low counts."""
        scorer = ImportanceScorer()
        for i in range(10):
            scorer.add_metric(f"sym_{i}", ImportanceMetrics(
                imported_by_count=i * 10,
                is_exported=(i > 7),
                has_docstring=(i > 5),
            ))
        summary = scorer.export_metrics_summary()
        assert "distribution" in summary
        dist = summary["distribution"]
        assert "high_importance" in dist
        assert "medium_importance" in dist
        assert "low_importance" in dist

    def test_summary_total_matches_cache(self):
        """total_symbols equals cache size."""
        scorer = ImportanceScorer()
        for i in range(5):
            scorer.add_metric(f"sym_{i}", ImportanceMetrics())
        summary = scorer.export_metrics_summary()
        assert summary["total_symbols"] == 5
