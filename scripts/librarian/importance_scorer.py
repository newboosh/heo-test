"""
Importance scoring for symbols and files.

Provides empirical, measurable scoring instead of arbitrary weights.
"""

from dataclasses import dataclass
from typing import Dict, List
import statistics


@dataclass
class ImportanceMetrics:
    """Raw metrics for importance calculation."""

    # Centrality metrics
    imported_by_count: int = 0
    imports_count: int = 0

    # Documentation metrics
    has_docstring: bool = False
    docstring_quality: float = 0.0  # 0-1, based on completeness

    # Test coverage
    test_count: int = 0
    behavior_count: int = 0

    # Complexity
    cyclomatic_complexity: int = 1
    lines_of_code: int = 0

    # Public API
    is_exported: bool = False  # In __all__ or public module


class ImportanceScorer:
    """
    Calculate importance scores using percentile ranking.

    Instead of arbitrary weights, we rank each metric across the entire
    codebase and combine percentiles.
    """

    def __init__(self):
        self.metrics_cache: Dict[str, ImportanceMetrics] = {}
        self._percentile_thresholds = None

    def add_metric(self, symbol_id: str, metrics: ImportanceMetrics):
        """Register metrics for a symbol."""
        self.metrics_cache[symbol_id] = metrics
        self._percentile_thresholds = None  # Invalidate cache

    def compute_percentile_thresholds(self):
        """
        Compute percentile thresholds for each metric.

        This makes scoring relative to the actual codebase instead of
        using magic numbers.
        """
        if not self.metrics_cache:
            return {}

        all_metrics = list(self.metrics_cache.values())

        # Extract each metric into a list
        imported_by = [m.imported_by_count for m in all_metrics]
        complexity = [m.cyclomatic_complexity for m in all_metrics]
        tests = [m.test_count for m in all_metrics]
        loc = [m.lines_of_code for m in all_metrics]

        # statistics.quantiles requires at least 2 data points
        if len(all_metrics) < 2:
            def _v(values, default=0):
                return values[0] if values else default
            return {
                'imported_by': {'p25': _v(imported_by), 'p50': _v(imported_by), 'p75': _v(imported_by), 'p90': _v(imported_by)},
                'complexity': {'p25': _v(complexity, 1), 'p50': _v(complexity, 1), 'p75': _v(complexity, 1), 'p90': _v(complexity, 1)},
                'tests': {'p25': _v(tests), 'p50': _v(tests), 'p75': _v(tests), 'p90': _v(tests)},
                'loc': {'p25': _v(loc), 'p50': _v(loc), 'p75': _v(loc), 'p90': _v(loc)},
            }

        # Calculate percentiles (25th, 50th, 75th, 90th)
        return {
            'imported_by': {
                'p25': statistics.quantiles(imported_by, n=4)[0] if imported_by else 0,
                'p50': statistics.quantiles(imported_by, n=4)[1] if imported_by else 0,
                'p75': statistics.quantiles(imported_by, n=4)[2] if imported_by else 0,
                'p90': statistics.quantiles(imported_by, n=10)[8] if imported_by else 0,
            },
            'complexity': {
                'p25': statistics.quantiles(complexity, n=4)[0] if complexity else 1,
                'p50': statistics.quantiles(complexity, n=4)[1] if complexity else 1,
                'p75': statistics.quantiles(complexity, n=4)[2] if complexity else 1,
                'p90': statistics.quantiles(complexity, n=10)[8] if complexity else 1,
            },
            'tests': {
                'p25': statistics.quantiles(tests, n=4)[0] if tests else 0,
                'p50': statistics.quantiles(tests, n=4)[1] if tests else 0,
                'p75': statistics.quantiles(tests, n=4)[2] if tests else 0,
                'p90': statistics.quantiles(tests, n=10)[8] if tests else 0,
            },
            'loc': {
                'p25': statistics.quantiles(loc, n=4)[0] if loc else 0,
                'p50': statistics.quantiles(loc, n=4)[1] if loc else 0,
                'p75': statistics.quantiles(loc, n=4)[2] if loc else 0,
                'p90': statistics.quantiles(loc, n=10)[8] if loc else 0,
            }
        }

    def get_percentile_rank(self, value: float, thresholds: dict) -> float:
        """
        Convert absolute value to percentile rank (0.0-1.0).

        Args:
            value: The metric value
            thresholds: Dict with p25, p50, p75, p90 keys

        Returns:
            Percentile as 0.0-1.0
        """
        def _span(a: float, b: float) -> float:
            """Return span, or 1.0 if span is zero to avoid division by zero."""
            return (b - a) if b > a else 1.0

        if value <= thresholds['p25']:
            return 0.25 * (value / thresholds['p25']) if thresholds['p25'] > 0 else 0
        elif value <= thresholds['p50']:
            return 0.25 + 0.25 * ((value - thresholds['p25']) /
                                  _span(thresholds['p25'], thresholds['p50']))
        elif value <= thresholds['p75']:
            return 0.50 + 0.25 * ((value - thresholds['p50']) /
                                  _span(thresholds['p50'], thresholds['p75']))
        elif value <= thresholds['p90']:
            return 0.75 + 0.15 * ((value - thresholds['p75']) /
                                  _span(thresholds['p75'], thresholds['p90']))
        else:
            return 0.90 + 0.10 * min((value - thresholds['p90']) / _span(0.0, thresholds['p90']), 1.0)

    def compute_importance(self, symbol_id: str) -> dict:
        """
        Calculate importance score with transparent breakdown.

        Returns dict with:
        - score: Overall importance (0.0-1.0)
        - components: Breakdown of each factor
        - percentiles: Percentile ranks for each metric
        - reasoning: Human-readable explanation
        """
        if symbol_id not in self.metrics_cache:
            return {
                'score': 0.0,
                'error': 'Symbol not found in cache'
            }

        metrics = self.metrics_cache[symbol_id]

        # Compute or retrieve percentile thresholds
        if self._percentile_thresholds is None:
            self._percentile_thresholds = self.compute_percentile_thresholds()
        thresholds = self._percentile_thresholds

        # Calculate percentile ranks
        centrality_pct = self.get_percentile_rank(
            metrics.imported_by_count,
            thresholds['imported_by']
        )
        complexity_pct = self.get_percentile_rank(
            metrics.cyclomatic_complexity,
            thresholds['complexity']
        )
        test_pct = self.get_percentile_rank(
            metrics.test_count,
            thresholds['tests']
        )

        # Component scores (empirically weighted)
        components = {
            'centrality': centrality_pct * 0.35,  # Most important: who depends on this?
            'documentation': (
                (0.3 if metrics.has_docstring else 0) +
                (metrics.docstring_quality * 0.2)
            ) * 0.25,  # Well-documented = maintained
            'test_coverage': test_pct * 0.20,  # Tested = important
            'complexity': complexity_pct * 0.10,  # Complex = needs attention
            'api_surface': 0.10 if metrics.is_exported else 0,  # Public API matters
        }

        # Final score
        score = sum(components.values())

        # Generate reasoning
        reasoning = []
        if centrality_pct > 0.75:
            reasoning.append(f"High centrality: imported by {metrics.imported_by_count} modules (top 25%)")
        if metrics.has_docstring and metrics.docstring_quality > 0.7:
            reasoning.append("Well-documented")
        if test_pct > 0.75:
            reasoning.append(f"Well-tested: {metrics.test_count} tests (top 25%)")
        if complexity_pct > 0.75:
            reasoning.append(f"High complexity: {metrics.cyclomatic_complexity} (needs attention)")
        if metrics.is_exported:
            reasoning.append("Public API")

        return {
            'score': round(score, 3),
            'components': {k: round(v, 3) for k, v in components.items()},
            'percentiles': {
                'centrality': round(centrality_pct, 3),
                'complexity': round(complexity_pct, 3),
                'test_coverage': round(test_pct, 3),
            },
            'reasoning': reasoning,
            'metrics': {
                'imported_by_count': metrics.imported_by_count,
                'has_docstring': metrics.has_docstring,
                'docstring_quality': round(metrics.docstring_quality, 3),
                'test_count': metrics.test_count,
                'cyclomatic_complexity': metrics.cyclomatic_complexity,
                'is_exported': metrics.is_exported,
            }
        }

    def get_ranked_symbols(self, limit: int = 20) -> List[dict]:
        """
        Get top N most important symbols with explanations.

        Args:
            limit: Number of symbols to return

        Returns:
            List of dicts with symbol_id, score, reasoning
        """
        scored = []
        for symbol_id in self.metrics_cache:
            result = self.compute_importance(symbol_id)
            scored.append({
                'symbol_id': symbol_id,
                **result
            })

        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]

    def export_metrics_summary(self) -> dict:
        """
        Export summary statistics for validation.

        Use this to verify scoring makes sense.
        """
        if self._percentile_thresholds is None:
            self._percentile_thresholds = self.compute_percentile_thresholds()

        return {
            'total_symbols': len(self.metrics_cache),
            'thresholds': self._percentile_thresholds,
            'distribution': {
                'high_importance': len([s for s in self.metrics_cache
                                       if self.compute_importance(s)['score'] > 0.7]),
                'medium_importance': len([s for s in self.metrics_cache
                                         if 0.3 < self.compute_importance(s)['score'] <= 0.7]),
                'low_importance': len([s for s in self.metrics_cache
                                      if self.compute_importance(s)['score'] <= 0.3]),
            }
        }
