#!/usr/bin/env python3
"""Tests for CodeRabbit loop components."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coderabbit.config import (
    MAX_ITERATIONS,
    MAX_STORED_COMMENTS,
    get_config,
)
from coderabbit.loop.branch_tracker import (
    get_worktree_prefix,
    is_owned_branch,
)
from coderabbit.loop.check_cr_response import (
    APPROVAL_INDICATORS,
    REJECTION_INDICATORS,
    check_cr_response,
)
from coderabbit.loop.comment_tracker import (
    load_tracker,
    save_tracker,
)
from coderabbit.loop.fetch_comments import (
    parse_suggested_fix,
)
from coderabbit.smart_resolver import (
    SECURITY_KEYWORDS,
    is_security_comment,
)


class TestConfig:
    """Tests for configuration module."""

    def test_max_iterations_default(self):
        """MAX_ITERATIONS should have a sensible default."""
        assert MAX_ITERATIONS >= 1
        assert MAX_ITERATIONS <= 20

    def test_max_stored_comments_default(self):
        """MAX_STORED_COMMENTS should have a sensible default."""
        assert MAX_STORED_COMMENTS >= 100
        assert MAX_STORED_COMMENTS <= 10000

    def test_get_config_returns_default(self):
        """get_config should return module default when no override."""
        result = get_config("MAX_ITERATIONS")
        assert result == MAX_ITERATIONS


class TestBranchTracker:
    """Tests for branch tracker module."""

    def test_get_worktree_prefix_two_dashes(self):
        """Should extract prefix with 2 dashes."""
        with patch("coderabbit.loop.branch_tracker.get_worktree_branch") as mock:
            mock.return_value = "05--feature-name"
            prefix = get_worktree_prefix()
            assert prefix == "05--"

    def test_get_worktree_prefix_three_dashes_legacy(self):
        """Should extract prefix with 3 dashes (legacy)."""
        with patch("coderabbit.loop.branch_tracker.get_worktree_branch") as mock:
            mock.return_value = "05---legacy-name"
            prefix = get_worktree_prefix()
            assert prefix == "05---"

    def test_get_worktree_prefix_no_dashes(self):
        """Should return None for branches without prefix pattern."""
        with patch("coderabbit.loop.branch_tracker.get_worktree_branch") as mock:
            mock.return_value = "main"
            prefix = get_worktree_prefix()
            assert prefix is None

    def test_get_worktree_prefix_non_numeric(self):
        """Should return None for non-numeric prefixes."""
        with patch("coderabbit.loop.branch_tracker.get_worktree_branch") as mock:
            mock.return_value = "feature--something"
            prefix = get_worktree_prefix()
            assert prefix is None

    def test_is_owned_branch_direct_match(self):
        """Should recognize directly owned branches."""
        with patch("coderabbit.loop.branch_tracker.get_owned_branches") as mock_owned:
            with patch("coderabbit.loop.branch_tracker.get_worktree_prefix") as mock_prefix:
                mock_owned.return_value = ["05--feature"]
                mock_prefix.return_value = "05--"
                assert is_owned_branch("05--feature") is True

    def test_is_owned_branch_prefix_match(self):
        """Should recognize branches by prefix."""
        with patch("coderabbit.loop.branch_tracker.get_owned_branches") as mock_owned:
            with patch("coderabbit.loop.branch_tracker.get_worktree_prefix") as mock_prefix:
                mock_owned.return_value = ["05--feature"]
                mock_prefix.return_value = "05--"
                assert is_owned_branch("05--other-branch") is True

    def test_is_owned_branch_not_owned(self):
        """Should reject branches from other worktrees."""
        with patch("coderabbit.loop.branch_tracker.get_owned_branches") as mock_owned:
            with patch("coderabbit.loop.branch_tracker.get_worktree_prefix") as mock_prefix:
                mock_owned.return_value = ["05--feature"]
                mock_prefix.return_value = "05--"
                assert is_owned_branch("06--other-worktree") is False


class TestSecurityDetection:
    """Tests for security comment detection."""

    def test_is_security_comment_positive(self):
        """Should detect security-related comments."""
        assert is_security_comment("This has a SQL injection vulnerability") is True
        assert is_security_comment("XSS attack possible here") is True
        assert is_security_comment("Missing authentication check") is True
        assert is_security_comment("Password exposed in logs") is True

    def test_is_security_comment_negative(self):
        """Should not flag non-security comments."""
        assert is_security_comment("Consider using a more descriptive name") is False
        assert is_security_comment("This function is too long") is False
        assert is_security_comment("Add unit tests") is False

    def test_security_keywords_exist(self):
        """Should have security keywords defined."""
        assert len(SECURITY_KEYWORDS) > 0
        assert "injection" in SECURITY_KEYWORDS
        assert "xss" in SECURITY_KEYWORDS


class TestSuggestedFixParsing:
    """Tests for parsing suggested fixes from comments."""

    def test_parse_diff_block(self):
        """Should parse diff blocks."""
        body = """
Here's the fix:
```diff
- old code
+ new code
```
"""
        result = parse_suggested_fix(body)
        assert result is not None
        assert result["type"] == "diff"
        assert result["is_committable"] is True

    def test_parse_suggestion_block(self):
        """Should parse suggestion blocks."""
        body = """
```suggestion
const x = 1;
```
"""
        result = parse_suggested_fix(body)
        assert result is not None
        assert result["type"] == "suggestion"
        assert result["is_committable"] is True
        assert "const x = 1;" in result["new_code"]

    def test_parse_code_block_with_intent(self):
        """Should parse code blocks with replacement intent."""
        body = """
You should be using:
```python
def foo():
    pass
```
"""
        result = parse_suggested_fix(body)
        assert result is not None
        assert result["type"] == "code_block"
        assert result["is_committable"] is False  # Needs human verification

    def test_parse_no_suggestion(self):
        """Should return None when no suggestion present."""
        body = "This is just a comment with no code."
        result = parse_suggested_fix(body)
        assert result is None


class TestApprovalHeuristics:
    """Tests for CodeRabbit approval/rejection detection."""

    def test_approval_indicators_exist(self):
        """Should have approval indicators defined."""
        assert len(APPROVAL_INDICATORS) > 0

    def test_rejection_indicators_exist(self):
        """Should have rejection indicators defined."""
        assert len(REJECTION_INDICATORS) > 0

    def test_approval_indicators_format(self):
        """Approval indicators should be (phrase, weight) tuples."""
        for item in APPROVAL_INDICATORS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            phrase, weight = item
            assert isinstance(phrase, str)
            assert isinstance(weight, int)
            assert weight > 0

    def test_rejection_indicators_format(self):
        """Rejection indicators should be (phrase, weight, context_required) tuples."""
        for item in REJECTION_INDICATORS:
            assert isinstance(item, tuple)
            assert len(item) == 3
            phrase, weight, context_required = item
            assert isinstance(phrase, str)
            assert isinstance(weight, int)
            assert isinstance(context_required, bool)


class TestCommentTracker:
    """Tests for comment tracker with file locking."""

    def test_save_and_load_tracker(self):
        """Should save and load tracker data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("coderabbit.loop.comment_tracker.get_tracker_path") as mock_path:
                tracker_path = Path(tmpdir) / ".coderabbit-tracker.json"
                mock_path.return_value = tracker_path

                # Save data
                test_data = {
                    "version": 1,
                    "pr_count": 5,
                    "last_analysis": None,
                    "comments": [{"pr": 1, "body": "test"}],
                }
                save_tracker(test_data)

                # Load and verify
                loaded = load_tracker()
                assert loaded["pr_count"] == 5
                assert len(loaded["comments"]) == 1

    def test_tracker_enforces_size_limit(self):
        """Should enforce MAX_STORED_COMMENTS limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("coderabbit.loop.comment_tracker.get_tracker_path") as mock_path:
                with patch("coderabbit.loop.comment_tracker.MAX_STORED_COMMENTS", 10):
                    tracker_path = Path(tmpdir) / ".coderabbit-tracker.json"
                    mock_path.return_value = tracker_path

                    # Save data exceeding limit
                    test_data = {
                        "version": 1,
                        "pr_count": 0,
                        "last_analysis": None,
                        "comments": [{"id": i} for i in range(20)],
                    }
                    save_tracker(test_data)

                    # Load and verify truncation
                    loaded = load_tracker()
                    assert len(loaded["comments"]) == 10
                    # Should keep most recent (last 10)
                    assert loaded["comments"][0]["id"] == 10


class TestConflictResolver:
    """Tests for conflict resolver patterns."""

    def test_conflict_marker_pattern(self):
        """Should match conflict markers correctly."""
        import re
        from coderabbit.loop.conflict_resolver import get_conflict_details

        # Test multi-line conflict content
        content = """some code
<<<<<<< HEAD
our line 1
our line 2
=======
their line 1
their line 2
>>>>>>> branch
more code"""

        pattern = re.compile(
            r"<<<<<<< ([^\n]*)\n(.*?)=======\n(.*?)>>>>>>> ([^\n]*)\n",
            re.DOTALL
        )
        match = pattern.search(content)
        assert match is not None
        assert match.group(1) == "HEAD"
        assert "our line 1" in match.group(2)
        assert "their line 1" in match.group(3)
        assert match.group(4) == "branch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
