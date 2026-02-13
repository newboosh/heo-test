"""Tests for docstring linter component."""

import pytest
import tempfile
from pathlib import Path

from scripts.intelligence.components.docstring_linter import (
    DocstringLinter, GoogleDocstringParser, DocstringIssue
)


class TestGoogleDocstringParser:
    """Test Google-style docstring parsing."""

    def test_parse_simple_summary(self):
        """Test parsing simple summary-only docstring."""
        docstring = "Do something useful."
        result = GoogleDocstringParser.parse(docstring)

        assert result['summary'] == "Do something useful."
        assert result['description'] == ""
        assert result['args'] == {}
        assert result['returns'] is None

    def test_parse_with_description(self):
        """Test parsing docstring with description."""
        docstring = """Do something useful.

        This is a longer description that explains
        what the function does in more detail."""

        result = GoogleDocstringParser.parse(docstring)

        assert result['summary'] == "Do something useful."
        assert "longer description" in result['description']

    def test_parse_args_section(self):
        """Test parsing Args section."""
        docstring = """Do something.

        Args:
            param1: First parameter.
            param2: Second parameter.
        """

        result = GoogleDocstringParser.parse(docstring)

        assert 'param1' in result['args']
        assert 'param2' in result['args']
        assert result['args']['param1'] == "First parameter."
        assert result['args']['param2'] == "Second parameter."

    def test_parse_returns_section(self):
        """Test parsing Returns section."""
        docstring = """Do something.

        Returns:
            True if successful, False otherwise.
        """

        result = GoogleDocstringParser.parse(docstring)

        assert "True if successful" in result['returns']

    def test_parse_raises_section(self):
        """Test parsing Raises section."""
        docstring = """Do something.

        Raises:
            ValueError: When value is invalid.
            TypeError: When type is wrong.
        """

        result = GoogleDocstringParser.parse(docstring)

        assert len(result['raises']) == 2
        assert ('ValueError', 'When value is invalid.') in result['raises']
        assert ('TypeError', 'When type is wrong.') in result['raises']

    def test_parse_example_section(self):
        """Test parsing Example section."""
        docstring = """Do something.

        Example:
            >>> result = function()
            >>> print(result)
            True
        """

        result = GoogleDocstringParser.parse(docstring)

        assert ">>> result = function()" in result['example']

    def test_parse_empty_docstring(self):
        """Test parsing empty docstring."""
        result = GoogleDocstringParser.parse(None)

        assert result['summary'] is None
        assert result['description'] == ""
        assert result['args'] == {}


class TestDocstringLinter:
    """Test docstring linting functionality."""

    @pytest.fixture
    def test_module(self):
        """Create test module with various docstring scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test_module.py"
            module_file.write_text('''
"""Module docstring.

This module tests docstring linting.
"""

def good_function(param1: str, param2: int) -> bool:
    """Check if something is valid.

    Validates the input parameters and returns result.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        True if valid, False otherwise.
    """
    return True

def missing_docstring(value):
    return value * 2

def incomplete_docstring(param1: str, param2: int):
    """Check something.

    No Args or Returns section!
    """
    return param1 + str(param2)

class GoodClass:
    """A well-documented class.

    This class demonstrates proper documentation.

    Attributes:
        value: The stored value.
    """

    def __init__(self, value: str):
        """Initialize with a value."""
        self.value = value

class NoDocstring:
    pass

def _private_function():
    # Private functions don't need docstrings
    pass
''')
            yield str(module_file)

    def test_find_missing_docstring(self, test_module):
        """Test detection of missing docstrings."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        # Should find missing docstring on missing_docstring()
        missing = [i for i in issues if i.name == 'missing_docstring']
        assert len(missing) >= 1
        assert missing[0].issue_type == 'missing'

    def test_find_incomplete_docstring(self, test_module):
        """Test detection of incomplete docstrings."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        # Should find missing Args/Returns
        incomplete = [i for i in issues if i.name == 'incomplete_docstring']
        assert any(i.issue_type == 'args_mismatch' for i in incomplete)

    def test_skip_private_functions(self, test_module):
        """Test that private functions are skipped."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        # _private_function should not be in issues
        private_issues = [i for i in issues if i.name == '_private_function']
        assert len(private_issues) == 0

    def test_check_class_docstring(self, test_module):
        """Test checking class docstrings."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        # NoDocstring class should have an issue
        class_issues = [i for i in issues if i.name == 'NoDocstring']
        assert len(class_issues) >= 1
        assert class_issues[0].issue_type == 'missing'

    def test_issue_severity_levels(self, test_module):
        """Test that issues have appropriate severity levels."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        # Should have various severity levels
        severities = {i.severity for i in issues}
        assert len(severities) > 0  # Should have at least one issue

    def test_issue_has_suggestion(self, test_module):
        """Test that all issues have actionable suggestions."""
        linter = DocstringLinter()
        issues = linter.lint_file(test_module)

        for issue in issues:
            assert issue.suggestion is not None
            assert len(issue.suggestion) > 0

    def test_summary_by_severity(self, test_module):
        """Test summary statistics by severity."""
        linter = DocstringLinter()
        linter.lint_file(test_module)
        summary = linter.get_summary()

        assert summary['total'] > 0
        assert 'by_severity' in summary
        assert 'by_type' in summary

    def test_docstring_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = DocstringIssue(
            name='test_func',
            file='test.py',
            line=10,
            severity='error',
            issue_type='missing',
            message='No docstring',
            suggestion='Add a docstring'
        )

        d = issue.to_dict()
        assert d['name'] == 'test_func'
        assert d['severity'] == 'error'
        assert d['issue_type'] == 'missing'


class TestDocstringFormat:
    """Test docstring format compliance checking."""

    def test_summary_missing_period(self):
        """Test detection of missing period in summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def func(param: str):
    """Summary without period

    Args:
        param: Description.

    Returns:
        Result.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            format_issues = [i for i in issues if i.issue_type == 'format']
            assert len(format_issues) >= 1

    def test_summary_too_long(self):
        """Test detection of overly long summary line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def func(param: str):
    """This is a very long summary line that exceeds the recommended eighty character limit and should be split."""
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            long_summaries = [i for i in issues if 'too long' in i.message.lower()]
            assert len(long_summaries) >= 1


class TestArgumentDocumentation:
    """Test argument documentation checking."""

    def test_missing_arg_documentation(self):
        """Test detection of undocumented parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def func(param1: str, param2: int) -> None:
    """Do something.

    Args:
        param1: First parameter.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # param2 should be flagged as missing
            missing_args = [i for i in issues if 'param2' in i.message]
            assert len(missing_args) >= 1

    def test_extra_arg_documentation(self):
        """Test detection of documented parameters not in signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def func(param1: str) -> None:
    """Do something.

    Args:
        param1: First parameter.
        param2: Extra parameter.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # param2 should be flagged as not in signature
            extra_args = [i for i in issues if 'param2' in i.message]
            assert len(extra_args) >= 1


class TestReturnDocumentation:
    """Test return value documentation."""

    def test_missing_return_documentation(self):
        """Test detection of missing return documentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def func(x: int) -> bool:
    """Do something."""
    return x > 0
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should flag missing Returns
            return_issues = [i for i in issues if 'return' in i.message.lower()]
            assert len(return_issues) >= 1


class TestAsyncFunctions:
    """Test async function linting."""

    def test_async_function_missing_docstring(self):
        """Test detection of missing docstring on async function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
async def fetch_data(url):
    return await some_request(url)
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should flag missing docstring on async function
            missing = [i for i in issues if i.name == 'fetch_data' and i.issue_type == 'missing']
            assert len(missing) >= 1

    def test_async_function_with_docstring(self):
        """Test that well-documented async function passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
async def fetch_data(url: str) -> dict:
    """Fetch data from a URL.

    Args:
        url: The URL to fetch from.

    Returns:
        The fetched data as a dictionary.
    """
    return await some_request(url)
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should have no missing docstring errors for fetch_data
            fetch_issues = [i for i in issues if i.name == 'fetch_data' and i.issue_type == 'missing']
            assert len(fetch_issues) == 0


class TestArgsKwargsHandling:
    """Test *args and **kwargs documentation."""

    def test_args_kwargs_documented(self):
        """Test that *args and **kwargs are properly checked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def flexible_func(required: str, *args, **kwargs) -> None:
    """Do something flexible.

    Args:
        required: A required parameter.
        args: Variable positional arguments.
        kwargs: Variable keyword arguments.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should have no args_mismatch errors
            args_issues = [i for i in issues if i.name == 'flexible_func' and i.issue_type == 'args_mismatch']
            assert len(args_issues) == 0

    def test_args_kwargs_undocumented(self):
        """Test that undocumented *args/**kwargs are flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def flexible_func(required: str, *args, **kwargs) -> None:
    """Do something flexible.

    Args:
        required: A required parameter.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should flag undocumented args and kwargs
            args_issues = [i for i in issues if i.name == 'flexible_func' and i.issue_type == 'args_mismatch']
            assert len(args_issues) >= 2  # args and kwargs both missing

    def test_keyword_only_args(self):
        """Test that keyword-only arguments are checked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def kw_only_func(pos: str, *, kw_only: int) -> None:
    """Function with keyword-only argument.

    Args:
        pos: Positional argument.
        kw_only: Keyword-only argument.
    """
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should have no args_mismatch errors
            args_issues = [i for i in issues if i.name == 'kw_only_func' and i.issue_type == 'args_mismatch']
            assert len(args_issues) == 0


class TestSummaryPunctuation:
    """Test summary line punctuation handling."""

    def test_summary_with_exclamation(self):
        """Test that summary ending with ! is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def important_func() -> None:
    """Do this immediately!"""
    pass
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should not flag exclamation mark as format issue
            format_issues = [i for i in issues if i.name == 'important_func' and 'punctuation' in i.message.lower()]
            assert len(format_issues) == 0

    def test_summary_with_question(self):
        """Test that summary ending with ? is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            module_file = Path(tmpdir) / "test.py"
            module_file.write_text('''
def check_func() -> bool:
    """Is this valid?"""
    return True
''')
            linter = DocstringLinter()
            issues = linter.lint_file(str(module_file))

            # Should not flag question mark as format issue
            format_issues = [i for i in issues if i.name == 'check_func' and 'punctuation' in i.message.lower()]
            assert len(format_issues) == 0
