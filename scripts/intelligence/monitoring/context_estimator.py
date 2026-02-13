"""Context window impact estimation for Claude models.

Estimates how many tokens the generated index will consume
in different Claude models and warns if usage is too high.
"""

import math
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ContextEstimate:
    """Context window usage estimate for a model."""

    model: str
    """Model name (e.g., "haiku", "sonnet", "opus")."""

    total_budget: int
    """Total context window tokens available."""

    estimated_tokens: int
    """Estimated tokens for this index."""

    usage_percent: float
    """Usage as percentage of budget."""

    is_safe: bool
    """True if usage < 50% of budget."""

    recommendation: str
    """Human-readable recommendation."""


class ContextEstimator:
    """Estimate context window impact of code intelligence index.

    Models and budgets:
    - Haiku: 100k context
    - Sonnet: 200k context
    - Opus: 200k context
    """

    # Model budgets in tokens
    MODEL_BUDGETS: Dict[str, int] = {
        "haiku": 100_000,
        "sonnet": 200_000,
        "opus": 200_000,
    }

    # Rough token estimates per component
    # Based on empirical testing
    TOKEN_ESTIMATES: Dict[str, int] = {
        "index_base": 500,  # Base overhead for structure
        "per_symbol": 20,   # Tokens per symbol (name + docstring)
        "per_file": 15,    # Tokens per file classification
        "per_dependency": 10,  # Tokens per import relationship
    }

    # Safe usage threshold (warn if exceeds this percentage)
    SAFE_THRESHOLD_PCT = 50

    def __init__(self):
        """Initialize context estimator."""
        pass

    def estimate_tokens(self, index_size: Dict[str, int], model: str = "haiku") -> ContextEstimate:
        """Estimate token usage for an index.

        Args:
            index_size: Dict with keys:
                - symbols: number of symbols found
                - files: number of files classified
                - dependencies: number of import relationships
            model: Model name (haiku, sonnet, opus).

        Returns:
            ContextEstimate with usage metrics.

        Raises:
            ValueError: If model not recognized.
        """
        if model not in self.MODEL_BUDGETS:
            raise ValueError(f"Unknown model: {model}. Must be one of {list(self.MODEL_BUDGETS.keys())}")

        # Estimate tokens
        tokens = self.TOKEN_ESTIMATES["index_base"]
        tokens += index_size.get("symbols", 0) * self.TOKEN_ESTIMATES["per_symbol"]
        tokens += index_size.get("files", 0) * self.TOKEN_ESTIMATES["per_file"]
        tokens += index_size.get("dependencies", 0) * self.TOKEN_ESTIMATES["per_dependency"]

        # Calculate usage percentage
        budget = self.MODEL_BUDGETS[model]
        usage_percent = (tokens / budget) * 100

        # Determine safety
        is_safe = usage_percent < self.SAFE_THRESHOLD_PCT

        # Generate recommendation
        if is_safe:
            recommendation = f"✅ SAFE - {usage_percent:.1f}% of {model.upper()} budget"
        else:
            other_models = [m for m in self.MODEL_BUDGETS if m != model]
            larger_models = [m for m in other_models if self.MODEL_BUDGETS[m] > budget]

            if larger_models:
                recommendation = f"⚠️  LARGE - {usage_percent:.1f}% of {model.upper()}, consider {larger_models[0].upper()}"
            else:
                recommendation = f"❌ TOO LARGE - {usage_percent:.1f}% of {model.upper()} budget"

        return ContextEstimate(
            model=model,
            total_budget=budget,
            estimated_tokens=tokens,
            usage_percent=usage_percent,
            is_safe=is_safe,
            recommendation=recommendation
        )

    def recommend_model(self, index_size: Dict[str, int]) -> str:
        """Recommend best model for this index size.

        Args:
            index_size: Dict with symbols, files, dependencies counts.

        Returns:
            Recommended model name.
        """
        estimates = {}
        for model in self.MODEL_BUDGETS:
            estimate = self.estimate_tokens(index_size, model)
            estimates[model] = estimate.usage_percent

        # Find model with lowest safe usage, or if all too large, the biggest
        safe_models = [(m, pct) for m, pct in estimates.items() if pct < self.SAFE_THRESHOLD_PCT]

        if safe_models:
            # Return smallest safe model (by budget, not by usage percent)
            return min(safe_models, key=lambda x: self.MODEL_BUDGETS[x[0]])[0]
        else:
            # All too large, use biggest
            return max(estimates.items(), key=lambda x: self.MODEL_BUDGETS[x[0]])[0]

    def format_report(self, index_size: Dict[str, int], model: str = "haiku") -> str:
        """Format context estimate as human-readable report.

        Args:
            index_size: Dict with symbols, files, dependencies.
            model: Model to estimate for.

        Returns:
            Formatted report string.
        """
        estimate = self.estimate_tokens(index_size, model)

        report = f"📈 Context impact: {estimate.estimated_tokens:,} tokens "
        report += f"({estimate.usage_percent:.1f}% of {model.upper()} budget) "
        report += estimate.recommendation

        return report
