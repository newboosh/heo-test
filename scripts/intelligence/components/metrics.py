"""Code metrics - complexity and coupling analysis.

Computes:
- Cyclomatic complexity (CC)
- Lines of code (LOC)
- Coupling (imports and dependencies)
- Method count per class
"""

import ast
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from scripts.intelligence.utils import ast_utils, file_utils


@dataclass
class Metrics:
    """Code metrics for a symbol."""

    name: str
    """Symbol name."""

    file: str
    """File path."""

    type: str
    """Symbol type: function, class, module."""

    loc: int
    """Lines of code (actual, not blank/comment)."""

    complexity: int
    """Cyclomatic complexity."""

    coupling: int
    """Number of imports/dependencies."""

    methods: int = 0
    """For classes: number of methods."""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class MetricsAnalyzer:
    """Analyze code metrics for complexity and coupling."""

    def __init__(self):
        """Initialize metrics analyzer."""
        self.metrics: Dict[str, Metrics] = {}

    def analyze_file(self, file_path: str) -> Dict[str, Metrics]:
        """Analyze metrics for all symbols in file.

        Args:
            file_path: Path to Python file.

        Returns:
            Dict mapping symbol names to metrics.
        """
        tree = ast_utils.parse_python_file(file_path)
        if not tree:
            return {}

        file_metrics = {}

        # Analyze module-level metrics
        file_content = file_utils.read_file(file_path)
        if file_content:
            module_loc = len([l for l in file_content.split('\n') if l.strip() and not l.strip().startswith('#')])
            module_complexity = self._calculate_complexity(tree)
            imports = ast_utils.get_imports(tree)
            total_imports = len(imports.get('import', [])) + len(imports.get('from', []))

            file_metrics[Path(file_path).stem] = Metrics(
                name=Path(file_path).stem,
                file=file_path,
                type='module',
                loc=module_loc,
                complexity=module_complexity,
                coupling=total_imports
            )

        # Analyze functions
        for func in ast_utils.get_function_defs(tree):
            metrics = self._analyze_function(func, file_path)
            file_metrics[func.name] = metrics

        # Analyze classes
        for cls in ast_utils.get_class_defs(tree):
            metrics = self._analyze_class(cls, file_path)
            file_metrics[cls.name] = metrics

        self.metrics.update(file_metrics)
        return file_metrics

    def _analyze_function(self, func: ast.FunctionDef, file_path: str) -> Metrics:
        """Analyze function metrics.

        Args:
            func: FunctionDef node.
            file_path: File path.

        Returns:
            Metrics object.
        """
        loc = func.end_lineno - func.lineno if hasattr(func, 'end_lineno') else 1
        complexity = self._calculate_complexity(func)

        return Metrics(
            name=func.name,
            file=file_path,
            type='function',
            loc=max(1, loc),
            complexity=complexity,
            coupling=self._count_dependencies(func)
        )

    def _analyze_class(self, cls: ast.ClassDef, file_path: str) -> Metrics:
        """Analyze class metrics.

        Args:
            cls: ClassDef node.
            file_path: File path.

        Returns:
            Metrics object.
        """
        loc = cls.end_lineno - cls.lineno if hasattr(cls, 'end_lineno') else 1
        complexity = self._calculate_complexity(cls)
        methods = ast_utils.get_class_methods(cls)

        return Metrics(
            name=cls.name,
            file=file_path,
            type='class',
            loc=max(1, loc),
            complexity=complexity,
            coupling=self._count_dependencies(cls),
            methods=len(methods)
        )

    @staticmethod
    def _calculate_complexity(node: ast.AST) -> int:
        """Calculate cyclomatic complexity.

        Counts decision points: if, elif, else, for, while, except, with, etc.

        Args:
            node: AST node to analyze.

        Returns:
            Cyclomatic complexity (minimum 1).
        """
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                # Count each except handler once (not via Try node to avoid double-counting)
                complexity += 1
            elif isinstance(child, (ast.BoolOp)):
                # and/or operators add complexity
                complexity += len(child.values) - 1

        return max(1, complexity)

    @staticmethod
    def _count_dependencies(node: ast.AST) -> int:
        """Count external function/class calls.

        Args:
            node: AST node to analyze.

        Returns:
            Count of likely external references.
        """
        calls = ast_utils.get_function_calls(ast.Module(body=[node] if isinstance(node, ast.stmt) else []))
        # External calls are those not starting with self, super, or builtins
        external = [c for c in calls if not c.startswith(('self.', 'super.'))]
        return len(external)

    def get_complexity_range(self) -> tuple:
        """Get min/max complexity in analyzed code.

        Returns:
            Tuple of (min, max) complexity.
        """
        if not self.metrics:
            return (0, 0)

        complexities = [m.complexity for m in self.metrics.values()]
        return (min(complexities), max(complexities))

    def get_high_complexity_symbols(self, threshold: int = 10) -> list:
        """Get symbols with high complexity.

        Args:
            threshold: Complexity threshold.

        Returns:
            List of high-complexity symbols.
        """
        return [m for m in self.metrics.values() if m.complexity >= threshold]
