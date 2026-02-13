"""Importance scoring - ranks symbols by importance using percentile-based metrics.

Scores based on:
- Test coverage (number of tests)
- Complexity (higher = more important)
- Coupling (higher = more important for others)
- Usage (how many other symbols use it)

Design principle: Numbers are only used for computed values (counts, percentiles).
Agent decisions use words (high, medium, low, none).
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from scripts.intelligence.components.metrics import Metrics


# Agent decisions expressed as words, not numbers
IMPORTANCE_LEVELS = ("none", "low", "medium", "high", "critical")


@dataclass
class ImportanceScore:
    """Importance score for a symbol."""

    name: str
    """Symbol name."""

    file: str
    """File path."""

    percentile: float
    """Percentile ranking (0-100) - computed from actual data."""

    factors: Dict[str, str]
    """Individual factor levels (words: none/low/medium/high/critical)."""

    raw_metrics: Dict[str, int]
    """Raw computed metrics (test_count, complexity, dependents)."""

    reasoning: str
    """Explanation of importance."""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def level(self) -> str:
        """Overall importance level derived from percentile.

        Returns:
            Word-based level: none, low, medium, high, critical.
        """
        if self.percentile >= 90:
            return "critical"
        elif self.percentile >= 75:
            return "high"
        elif self.percentile >= 50:
            return "medium"
        elif self.percentile >= 25:
            return "low"
        return "none"


class ImportanceScorer:
    """Score importance of symbols using multiple metrics.

    All factor assessments use words (none/low/medium/high/critical).
    Only computed values (counts, percentiles) are numbers.
    """

    def __init__(self):
        """Initialize scorer."""
        self.scores: List[ImportanceScore] = []
        self._raw_scores: List[float] = []  # Internal for percentile calc

    def score_symbols(self, metrics: Dict[str, Metrics],
                     test_coverage: Dict[str, int],
                     coupling_graph: Dict[str, set],
                     all_symbols_count: int) -> List[ImportanceScore]:
        """Score all symbols for importance.

        Args:
            metrics: Dict of symbol metrics.
            test_coverage: Dict mapping symbol names to test counts.
            coupling_graph: Dict of symbol to dependents.
            all_symbols_count: Total number of symbols in codebase.

        Returns:
            List of importance scores.
        """
        self.scores = []
        self._raw_scores = []

        # First pass: collect raw metrics for percentile calculation
        raw_data = []
        for name, metric in metrics.items():
            test_count = test_coverage.get(name, 0)
            dependents = len(coupling_graph.get(name, set()))
            # Composite raw score for ranking (sum of normalized metrics)
            raw_score = test_count + metric.complexity + dependents
            raw_data.append((name, metric, test_count, dependents, raw_score))
            self._raw_scores.append(raw_score)

        # Second pass: create scores with percentiles
        for name, metric, test_count, dependents, raw_score in raw_data:
            percentile = self._calculate_percentile(raw_score, self._raw_scores)

            factors = self._assess_factors(
                test_count, metric.complexity, dependents, metric.type
            )

            raw_metrics = {
                "test_count": test_count,
                "complexity": metric.complexity,
                "dependents": dependents,
            }

            reasoning = self._generate_reasoning(factors, raw_metrics, metric.type)

            score = ImportanceScore(
                name=name,
                file=metric.file,
                percentile=percentile,
                factors=factors,
                raw_metrics=raw_metrics,
                reasoning=reasoning,
            )
            self.scores.append(score)

        return self.scores

    @staticmethod
    def _assess_factors(test_count: int, complexity: int,
                       dependents: int, symbol_type: str) -> Dict[str, str]:
        """Assess factor levels using words, not numbers.

        Args:
            test_count: Number of tests covering this symbol.
            complexity: Cyclomatic complexity.
            dependents: Number of symbols depending on this.
            symbol_type: Type of symbol (class, function, etc).

        Returns:
            Dict of factor names to word-based levels.
        """
        factors = {}

        # Test coverage: assessed by presence and quantity
        if test_count == 0:
            factors["test_coverage"] = "none"
        elif test_count == 1:
            factors["test_coverage"] = "low"
        elif test_count <= 3:
            factors["test_coverage"] = "medium"
        elif test_count <= 6:
            factors["test_coverage"] = "high"
        else:
            factors["test_coverage"] = "critical"

        # Complexity: assessed relative to typical code
        if complexity <= 1:
            factors["complexity"] = "none"
        elif complexity <= 3:
            factors["complexity"] = "low"
        elif complexity <= 7:
            factors["complexity"] = "medium"
        elif complexity <= 15:
            factors["complexity"] = "high"
        else:
            factors["complexity"] = "critical"

        # Coupling: assessed by dependent count
        if dependents == 0:
            factors["coupling"] = "none"
        elif dependents <= 2:
            factors["coupling"] = "low"
        elif dependents <= 5:
            factors["coupling"] = "medium"
        elif dependents <= 10:
            factors["coupling"] = "high"
        else:
            factors["coupling"] = "critical"

        # Type importance: classes and modules are architectural
        type_levels = {
            "class": "high",
            "module": "high",
            "function": "medium",
            "method": "low",
        }
        factors["type"] = type_levels.get(symbol_type, "low")

        return factors

    @staticmethod
    def _calculate_percentile(score: float, all_scores: List[float]) -> float:
        """Calculate percentile rank from raw scores.

        This is a computed value, so it returns a number.

        Args:
            score: Raw score to rank.
            all_scores: All raw scores in the dataset.

        Returns:
            Percentile (0-100).
        """
        if not all_scores or score is None:
            return 0.0

        below = sum(1 for s in all_scores if s < score)
        equal = sum(1 for s in all_scores if s == score)
        percentile = ((below + equal / 2) / len(all_scores)) * 100
        return round(percentile, 1)

    @staticmethod
    def _generate_reasoning(factors: Dict[str, str],
                           raw_metrics: Dict[str, int],
                           symbol_type: str) -> str:
        """Generate explanation using words and computed counts.

        Args:
            factors: Word-based factor assessments.
            raw_metrics: Computed metric values.
            symbol_type: Type of symbol.

        Returns:
            Human-readable reasoning string.
        """
        reasons = []

        # Test coverage reasoning
        coverage = factors.get("test_coverage", "none")
        test_count = raw_metrics.get("test_count", 0)
        if coverage in ("high", "critical"):
            reasons.append(f"well-tested ({test_count} tests)")
        elif coverage == "none":
            reasons.append("untested")

        # Complexity reasoning
        complexity_level = factors.get("complexity", "none")
        cc = raw_metrics.get("complexity", 0)
        if complexity_level in ("high", "critical"):
            reasons.append(f"complex (CC={cc})")

        # Coupling reasoning
        coupling = factors.get("coupling", "none")
        deps = raw_metrics.get("dependents", 0)
        if coupling in ("high", "critical"):
            reasons.append(f"highly coupled ({deps} dependents)")

        # Type reasoning
        if symbol_type == "class":
            reasons.append("class definition")
        elif symbol_type == "module":
            reasons.append("module-level")

        return "; ".join(reasons) if reasons else "standard symbol"

    def get_top_symbols(self, count: int = 10) -> List[ImportanceScore]:
        """Get top N most important symbols by percentile.

        Args:
            count: Number to return.

        Returns:
            Top symbols by computed percentile.
        """
        return sorted(
            self.scores,
            key=lambda s: s.percentile,
            reverse=True
        )[:count]

    def get_symbols_by_level(self, min_level: str = "high") -> List[ImportanceScore]:
        """Get symbols at or above importance level.

        Args:
            min_level: Minimum level (none/low/medium/high/critical).

        Returns:
            Symbols at or above the specified level.
        """
        level_order = {level: i for i, level in enumerate(IMPORTANCE_LEVELS)}
        min_idx = level_order.get(min_level, 0)
        return [s for s in self.scores if level_order.get(s.level, 0) >= min_idx]

    def get_symbols_by_percentile(self, min_percentile: float = 75) -> List[ImportanceScore]:
        """Get symbols above percentile threshold.

        Args:
            min_percentile: Minimum percentile (0-100), a computed threshold.

        Returns:
            Symbols above threshold.
        """
        return [s for s in self.scores if s.percentile >= min_percentile]
