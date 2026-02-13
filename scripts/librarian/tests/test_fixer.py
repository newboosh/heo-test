"""Tests for the fix context gathering module."""

import pytest
from pathlib import Path

from scripts.librarian.fixer import (
    gather_fix_context,
    generate_fix_prompt,
    save_fix_report,
)


class TestGatherFixContext:
    """Tests for gather_fix_context."""

    def test_empty_links_no_issues(self, tmp_path):
        """Clean links index with no problems returns zero issues."""
        links_index = {
            "generated": "", "total_links": 1, "total_broken": 0, "total_errors": 0,
            "docs": {
                "doc.md": {
                    "links": [
                        {"ref": "User", "target": "app/models/user.py::User",
                         "type": "class", "hash": "abc", "line": 5, "status": "CURRENT"}
                    ],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        report = gather_fix_context(root=tmp_path, links_index=links_index)
        assert report["total_issues"] == 0
        assert report["stale"] == 0
        assert report["broken"] == 0
        assert report["errors"] == 0

    def test_gather_stale_context(self, sample_python_project):
        """Stale link produces fix context with issue_type=stale."""
        root = sample_python_project
        links_index = {
            "generated": "", "total_links": 1, "total_broken": 0, "total_errors": 0,
            "docs": {
                "docs/api.md": {
                    "links": [
                        {"ref": "authenticate", "target": "app/services/auth.py::authenticate",
                         "type": "function", "hash": "old_hash", "line": 5, "status": "STALE"}
                    ],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        # Need the doc file to exist for find_doc_section_for_ref
        docs_dir = root / "docs"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / "api.md").write_text("# API\n\nSee `authenticate` here.\n")

        report = gather_fix_context(root=root, links_index=links_index)
        assert report["stale"] == 1
        stale_issues = [i for i in report["issues"] if i["issue_type"] == "stale"]
        assert len(stale_issues) == 1
        assert stale_issues[0]["ref"] == "authenticate"

    def test_gather_broken_context(self, tmp_path):
        """Broken ref produces fix context with issue_type=broken."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("# API\n\nSee `old_func` here.\n")

        links_index = {
            "generated": "", "total_links": 0, "total_broken": 1, "total_errors": 0,
            "docs": {
                "docs/api.md": {
                    "links": [],
                    "broken": [{"ref": "old_func", "line": 3, "reason": "not found"}],
                    "errors": [],
                }
            },
        }
        report = gather_fix_context(root=tmp_path, links_index=links_index)
        assert report["broken"] == 1
        broken_issues = [i for i in report["issues"] if i["issue_type"] == "broken"]
        assert len(broken_issues) == 1

    def test_gather_error_context(self, tmp_path):
        """Error ref produces fix context with issue_type=ambiguous."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("# API\n\nSee `helper` here.\n")

        links_index = {
            "generated": "", "total_links": 0, "total_broken": 0, "total_errors": 1,
            "docs": {
                "docs/api.md": {
                    "links": [],
                    "broken": [],
                    "errors": [{"ref": "helper", "line": 3,
                                "reason": "ambiguous", "candidates": ["a.py::helper", "b.py::helper"]}],
                }
            },
        }
        report = gather_fix_context(root=tmp_path, links_index=links_index)
        assert report["errors"] == 1
        error_issues = [i for i in report["issues"] if i["issue_type"] == "ambiguous"]
        assert len(error_issues) == 1
        assert error_issues[0]["candidates"] is not None

    def test_report_counts_match_issues(self, tmp_path):
        """Report counts match the actual issues list."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "doc.md").write_text("# Doc\n\nText.\n")

        links_index = {
            "generated": "", "total_links": 1, "total_broken": 1, "total_errors": 1,
            "docs": {
                "docs/doc.md": {
                    "links": [
                        {"ref": "a", "target": "a.py", "type": "file",
                         "hash": "old", "line": 1, "status": "STALE"}
                    ],
                    "broken": [{"ref": "b", "line": 2, "reason": "not found"}],
                    "errors": [{"ref": "c", "line": 3, "reason": "ambiguous",
                                "candidates": ["x", "y"]}],
                }
            },
        }
        report = gather_fix_context(root=tmp_path, links_index=links_index)
        assert report["total_issues"] == report["stale"] + report["broken"] + report["errors"]
        assert len(report["issues"]) == report["total_issues"]


class TestGenerateFixPrompt:
    """Tests for generate_fix_prompt."""

    def test_stale_prompt_includes_current_code(self):
        """Stale context with current_code includes code block."""
        context = {
            "doc_path": "docs/api.md",
            "ref": "authenticate",
            "line": 5,
            "issue_type": "stale",
            "reason": "Code has changed",
            "doc_section": "Authentication",
            "current_code": "def authenticate(user, pwd):\n    return True",
            "candidates": None,
        }
        prompt = generate_fix_prompt(context)
        assert "authenticate" in prompt
        assert "```python" in prompt
        assert "def authenticate" in prompt
        assert "Authentication" in prompt

    def test_broken_prompt_includes_candidates(self):
        """Broken context with candidates lists them."""
        context = {
            "doc_path": "docs/api.md",
            "ref": "old_func",
            "line": 10,
            "issue_type": "broken",
            "reason": "not found",
            "doc_section": None,
            "current_code": None,
            "candidates": ["app/new_func.py", "app/renamed.py"],
        }
        prompt = generate_fix_prompt(context)
        assert "old_func" in prompt
        assert "app/new_func.py" in prompt
        assert "app/renamed.py" in prompt

    def test_ambiguous_prompt_includes_candidates(self):
        """Ambiguous context lists candidate locations."""
        context = {
            "doc_path": "docs/api.md",
            "ref": "helper",
            "line": 3,
            "issue_type": "ambiguous",
            "reason": "found in 2 locations",
            "doc_section": "Utils",
            "current_code": None,
            "candidates": ["app/a.py::helper", "app/b.py::helper"],
        }
        prompt = generate_fix_prompt(context)
        assert "helper" in prompt
        assert "app/a.py::helper" in prompt
        assert "Qualify" in prompt or "disambiguat" in prompt.lower()

    def test_prompt_includes_ref_and_line(self):
        """All prompts include the ref text and line number."""
        context = {
            "doc_path": "docs/readme.md",
            "ref": "my_func",
            "line": 42,
            "issue_type": "stale",
            "reason": "Code changed",
            "doc_section": None,
            "current_code": None,
            "candidates": None,
        }
        prompt = generate_fix_prompt(context)
        assert "my_func" in prompt
        assert "42" in prompt


class TestSaveFixReport:
    """Tests for save_fix_report."""

    def test_save_creates_file(self, tmp_path):
        """save_fix_report writes a JSON file."""
        path = tmp_path / "fix_report.json"
        report = {
            "total_issues": 0,
            "stale": 0,
            "broken": 0,
            "errors": 0,
            "issues": [],
        }
        save_fix_report(report, path=path)
        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        """save_fix_report creates intermediate directories."""
        path = tmp_path / "a" / "b" / "fix_report.json"
        report = {
            "total_issues": 0,
            "stale": 0,
            "broken": 0,
            "errors": 0,
            "issues": [],
        }
        save_fix_report(report, path=path)
        assert path.exists()
