"""Content profiling - semantic summaries and categorization of code.

Generates semantic descriptions of symbols based on:
- Docstrings
- Function names and structure
- Complexity metrics
- Naming patterns
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import re

from scripts.intelligence.components.symbol_index import Symbol
from scripts.intelligence.components.metrics import Metrics


@dataclass
class ContentProfile:
    """Semantic summary of a symbol."""

    name: str
    """Symbol name."""

    file: str
    """File path."""

    summary: str
    """Generated semantic summary."""

    keywords: List[str]
    """Extracted keywords."""

    categories: List[str]
    """Semantic categories."""

    raw_docstring: Optional[str] = None
    """Original docstring."""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class ContentProfiler:
    """Generate semantic summaries and categorization."""

    def __init__(self):
        """Initialize profiler."""
        self.entries: List[ContentProfile] = []

    def index_symbols(self, symbols: List[Symbol],
                     metrics: Dict[str, Metrics]) -> List[ContentProfile]:
        """Generate content profile entries for symbols.

        Args:
            symbols: List of symbols.
            metrics: Metrics for symbols.

        Returns:
            List of content profile entries.
        """
        self.entries = []

        for symbol in symbols:
            metric = metrics.get(symbol.name)
            entry = self._generate_profile(symbol, metric)
            self.entries.append(entry)

        return self.entries

    def _generate_profile(self, symbol: Symbol,
                          metric: Optional[Metrics]) -> ContentProfile:
        """Generate content profile for single symbol.

        Args:
            symbol: Symbol to analyze.
            metric: Optional metrics.

        Returns:
            ContentProfile entry.
        """
        # Extract keywords from name and docstring
        keywords = self._extract_keywords(symbol.name, symbol.docstring)

        # Categorize based on name patterns and metrics
        categories = self._categorize_symbol(symbol, metric)

        # Generate summary
        summary = self._generate_summary(symbol, metric, categories)

        return ContentProfile(
            name=symbol.name,
            file=symbol.file,
            summary=summary,
            keywords=keywords,
            categories=categories,
            raw_docstring=symbol.docstring
        )

    @staticmethod
    def _extract_keywords(name: str, docstring: Optional[str]) -> List[str]:
        """Extract keywords from name and docstring.

        Args:
            name: Symbol name.
            docstring: Optional docstring.

        Returns:
            List of keywords.
        """
        keywords = set()

        # From name: split on underscores and camelCase
        name_parts = re.split(r'[_]', name)
        for part in name_parts:
            # Split camelCase
            camel_parts = re.findall(r'[A-Z][a-z]+|[a-z]+', part)
            keywords.update(camel_parts)

        # From docstring: extract nouns and action verbs
        if docstring:
            words = docstring.lower().split()
            # Common meaningful words (not too generic)
            meaningful = [w for w in words if len(w) > 3 and
                         not w.startswith(('the', 'and', 'for', 'with', 'from'))]
            keywords.update(meaningful[:10])  # Limit to top 10

        return sorted(list(keywords))[:5]  # Return top 5

    @staticmethod
    def _categorize_symbol(symbol: Symbol,
                          metric: Optional[Metrics]) -> List[str]:
        """Categorize symbol.

        Args:
            symbol: Symbol to categorize.
            metric: Optional metrics.

        Returns:
            List of categories.
        """
        categories = []

        # Type-based categories
        categories.append(f"type:{symbol.type}")

        # Name-based patterns
        name_lower = symbol.name.lower()
        if name_lower.startswith(('get_', 'set_', 'is_', 'has_')):
            categories.append("accessor")
        if name_lower.startswith(('test_', '_test', '__')):
            categories.append("test")
        if 'error' in name_lower or 'exception' in name_lower:
            categories.append("error-handling")
        if 'cache' in name_lower or 'pool' in name_lower:
            categories.append("resource-management")

        # Complexity-based categories
        if metric:
            if metric.complexity > 10:
                categories.append("high-complexity")
            elif metric.complexity > 5:
                categories.append("medium-complexity")

            if metric.coupling > 5:
                categories.append("high-coupling")

        return categories

    @staticmethod
    def _generate_summary(symbol: Symbol, metric: Optional[Metrics],
                         categories: List[str]) -> str:
        """Generate semantic summary.

        Args:
            symbol: Symbol.
            metric: Optional metrics.
            categories: Categories.

        Returns:
            Summary string.
        """
        parts = []

        # Start with docstring summary if available
        if symbol.docstring:
            first_line = symbol.docstring.split('\n')[0].strip()
            if first_line:
                parts.append(first_line)

        # Add information about symbol
        parts.append(f"Defined as {symbol.type} in {symbol.file}:{symbol.line}")

        # Add metrics info
        if metric:
            info = []
            info.append(f"complexity={metric.complexity}")
            info.append(f"coupling={metric.coupling}")
            if metric.loc > 0:
                info.append(f"loc={metric.loc}")
            parts.append(f"Metrics: {', '.join(info)}")

        # Add categories
        if categories:
            cat_str = ", ".join(c.replace('type:', '').replace('-', ' ')
                              for c in categories if not c.startswith('type:'))
            if cat_str:
                parts.append(f"Categories: {cat_str}")

        return " | ".join(parts)

    def search(self, query: str) -> List[ContentProfile]:
        """Search content profile index.

        Args:
            query: Search query.

        Returns:
            Matching entries.
        """
        query_lower = query.lower()
        results = []

        for entry in self.entries:
            # Match in summary, keywords, or name
            if (query_lower in entry.summary.lower() or
                query_lower in entry.name.lower() or
                any(query_lower in k for k in entry.keywords)):
                results.append(entry)

        return results

    def get_by_category(self, category: str) -> List[ContentProfile]:
        """Get entries by category.

        Args:
            category: Category name.

        Returns:
            Matching entries.
        """
        return [e for e in self.entries if category in e.categories]
