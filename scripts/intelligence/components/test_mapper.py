"""Test behavior mapping - maps tests to symbols using docstring analysis.

Maps test files to the symbols they test by analyzing:
- Test file docstrings (what they test)
- Test function names (naming patterns)
- Test file names (naming patterns)
- Import statements (what's imported)
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from scripts.intelligence.utils import ast_utils, file_utils
from scripts.intelligence.components.symbol_index import Symbol


@dataclass
class TestMapping:
    """Mapping between test and symbol."""

    test_file: str
    """Path to test file."""

    test_symbol: str
    """Name of test function/class."""

    symbol_file: str
    """Path to symbol being tested."""

    symbol_name: str
    """Name of symbol being tested."""

    confidence: str
    """Confidence level: high, medium, low."""

    reason: Optional[str] = None
    """Why this mapping was made."""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class TestMapper:
    """Map tests to symbols using heuristics and naming patterns."""

    def __init__(self):
        """Initialize test mapper."""
        self.mappings: List[TestMapping] = []

    def map_tests(self, symbols: List[Symbol], root_dir: str) -> List[TestMapping]:
        """Map test files to symbols.

        Args:
            symbols: List of extracted symbols.
            root_dir: Root directory for finding test files.

        Returns:
            List of test mappings.
        """
        self.mappings = []

        # Get all test files
        test_files = self._find_test_files(root_dir)

        # For each test file, find what it tests
        for test_file in test_files:
            test_mappings = self._map_test_file(test_file, symbols, root_dir)
            self.mappings.extend(test_mappings)

        return self.mappings

    def _find_test_files(self, root_dir: str) -> List[str]:
        """Find all test files in directory.

        Args:
            root_dir: Root directory to search.

        Returns:
            List of test file paths.
        """
        test_files = []

        for python_file in file_utils.get_python_files(root_dir):
            filename = Path(python_file).name
            # Check if file looks like a test
            if (filename.startswith('test_') or filename.endswith('_test.py') or
                'test' in filename.lower()):
                test_files.append(python_file)

        return test_files

    def _map_test_file(self, test_file: str, symbols: List[Symbol],
                      root_dir: str) -> List[TestMapping]:
        """Map a single test file to symbols.

        Args:
            test_file: Path to test file.
            symbols: List of all symbols.
            root_dir: Root directory.

        Returns:
            List of mappings for this test file.
        """
        mappings = []

        # Extract test functions from file
        tree = ast_utils.parse_python_file(test_file)
        if not tree:
            return mappings

        test_functions = ast_utils.get_function_defs(tree)
        test_classes = ast_utils.get_class_defs(tree)

        # Get imports from test file
        imports = ast_utils.get_imports(tree)

        # For each test function, find what it tests
        for func in test_functions:
            func_name = func.name
            func_doc = ast_utils.get_docstring(func)

            # Find matching symbols
            matching_symbols = self._find_matching_symbols(
                func_name, func_doc, imports, symbols, root_dir
            )

            for symbol in matching_symbols:
                confidence, reason = self._calculate_confidence(
                    func_name, func_doc, symbol
                )

                mapping = TestMapping(
                    test_file=test_file,
                    test_symbol=func_name,
                    symbol_file=symbol.file,
                    symbol_name=symbol.name,
                    confidence=confidence,
                    reason=reason
                )
                mappings.append(mapping)

        # Also map tests inside classes (e.g., unittest.TestCase)
        for cls in test_classes:
            cls_name = cls.name
            # Get methods from the class
            for method in ast_utils.get_function_defs(cls):
                method_name = method.name
                method_doc = ast_utils.get_docstring(method)

                matching_symbols = self._find_matching_symbols(
                    method_name, method_doc, imports, symbols, root_dir
                )

                for symbol in matching_symbols:
                    confidence, reason = self._calculate_confidence(
                        method_name, method_doc, symbol
                    )

                    mapping = TestMapping(
                        test_file=test_file,
                        test_symbol=f"{cls_name}.{method_name}",
                        symbol_file=symbol.file,
                        symbol_name=symbol.name,
                        confidence=confidence,
                        reason=reason
                    )
                    mappings.append(mapping)

        return mappings

    def _find_matching_symbols(self, test_name: str, test_doc: Optional[str],
                              imports: Dict, symbols: List[Symbol],
                              root_dir: str) -> List[Symbol]:
        """Find symbols matching this test.

        Args:
            test_name: Test function name.
            test_doc: Test docstring.
            imports: Imports from test file.
            symbols: All symbols.
            root_dir: Root directory.

        Returns:
            List of matching symbols.
        """
        matches = []

        # Extract what's being tested from function name
        # e.g., test_helper_function → helper_function
        target_name = self._extract_target_name(test_name)

        for symbol in symbols:
            # Match by name
            if symbol.name.lower() == target_name.lower():
                matches.append(symbol)
            # Match by docstring reference
            elif test_doc and symbol.name.lower() in test_doc.lower():
                matches.append(symbol)

        return matches

    @staticmethod
    def _extract_target_name(test_name: str) -> str:
        """Extract target symbol name from test name.

        Examples:
        - test_helper → helper
        - test_DataModel → DataModel
        - test_build_cache → build_cache

        Args:
            test_name: Test function/class name.

        Returns:
            Extracted target name.
        """
        # Remove common test prefixes
        name = test_name
        if name.startswith('test_'):
            name = name[5:]
        if name.endswith('_test'):
            name = name[:-5]

        return name

    @staticmethod
    def _calculate_confidence(test_name: str, test_doc: Optional[str],
                             symbol) -> Tuple[str, str]:
        """Calculate confidence of mapping.

        Args:
            test_name: Test name.
            test_doc: Test docstring.
            symbol: Symbol being tested.

        Returns:
            Tuple of (confidence_level, reason).
        """
        reason = ""

        # High confidence: name matches and has docstring
        if (test_name[5:] if test_name.startswith('test_') else test_name).lower() == symbol.name.lower():
            if test_doc:
                return "high", "Name match + docstring"
            else:
                return "high", "Name match"

        # Medium confidence: mentioned in docstring
        if test_doc and symbol.name.lower() in test_doc.lower():
            return "medium", "Mentioned in docstring"

        # Low confidence: weak heuristic match
        return "low", "Weak heuristic match"

    def get_coverage_for_symbol(self, symbol: Symbol) -> int:
        """Get number of tests for a symbol.

        Args:
            symbol: Symbol to check coverage for.

        Returns:
            Count of tests.
        """
        count = 0
        for mapping in self.mappings:
            if (mapping.symbol_name == symbol.name and
                mapping.symbol_file == symbol.file):
                count += 1
        return count
