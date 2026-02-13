"""Tests for the link staleness checker module."""

import pytest
from pathlib import Path

from scripts.librarian.checker import (
    check_all_links,
    get_stale_links,
    get_broken_refs,
    get_error_refs,
)
from scripts.librarian.symbol_indexer import build_symbol_index, save_index, INDEX_PATH
from scripts.librarian.reference_extractor import extract_all_references, save_refs, REFS_PATH
from scripts.librarian.resolver import resolve_all_references, save_links, LINKS_PATH


def _build_full_pipeline(root, monkeypatch):
    """Helper: run the full build pipeline and return the links index."""
    index = build_symbol_index(root=root, index_dirs=["app", "scripts"])
    save_index(index, path=root / INDEX_PATH)

    known = set(index["symbols"].keys())
    refs = extract_all_references(root, known_symbols=known)
    save_refs(refs, path=root / REFS_PATH)

    monkeypatch.chdir(root)
    links = resolve_all_references(root, index)
    save_links(links, path=root / LINKS_PATH)
    return links


class TestCheckAllLinks:
    """Tests for check_all_links."""

    def test_all_current_after_fresh_build(self, sample_markdown_docs, monkeypatch):
        """Links checked immediately after build should all be CURRENT."""
        root = sample_markdown_docs
        links = _build_full_pipeline(root, monkeypatch)
        assert links["total_links"] > 0, "Fixture should produce links"

        _updated_links, report = check_all_links(root, links)
        assert report["stale"] == 0
        assert report["current"] == report["total_checked"]

    def test_detect_stale_after_code_change(self, sample_markdown_docs, monkeypatch):
        """Modifying source code makes links STALE."""
        root = sample_markdown_docs
        links = _build_full_pipeline(root, monkeypatch)
        assert links["total_links"] > 0, "Fixture should produce links"

        # Modify a source file
        auth_file = root / "app" / "services" / "auth.py"
        auth_file.write_text(
            '"""Authentication service - MODIFIED."""\n'
            "\n"
            "def authenticate(username: str, password: str, mfa: bool = False) -> bool:\n"
            '    """Authenticate a user with optional MFA."""\n'
            "    return True\n"
        )

        _, report = check_all_links(root, links)
        assert report["stale"] > 0

    def test_detect_stale_after_file_deletion(self, sample_markdown_docs, monkeypatch):
        """Deleting a referenced file results in STALE links."""
        root = sample_markdown_docs
        links = _build_full_pipeline(root, monkeypatch)

        # Find a file-type link and delete the target
        file_links = []
        for doc_links in links["docs"].values():
            for link in doc_links["links"]:
                if link["type"] == "file":
                    file_links.append(link)
        assert file_links, "Fixture should produce file-type links"

        target = file_links[0]["target"]
        target_path = root / target
        if target_path.exists():
            target_path.unlink()

        _, report = check_all_links(root, links)
        assert report["stale"] > 0

    def test_report_metadata(self, sample_markdown_docs, monkeypatch):
        """Check report has correct metadata fields."""
        root = sample_markdown_docs
        links = _build_full_pipeline(root, monkeypatch)

        _, report = check_all_links(root, links)
        assert "checked" in report
        assert "total_checked" in report
        assert "current" in report
        assert "stale" in report
        assert report["current"] + report["stale"] == report["total_checked"]

    def test_links_index_mutated_with_status(self, sample_markdown_docs, monkeypatch):
        """check_all_links mutates links_index in place with status field."""
        root = sample_markdown_docs
        links = _build_full_pipeline(root, monkeypatch)
        assert links["total_links"] > 0, "Fixture should produce links"

        updated_links, _ = check_all_links(root, links)
        # Links should now have a "status" field
        for doc_links in updated_links["docs"].values():
            for link in doc_links["links"]:
                assert "status" in link
                assert link["status"] in ("CURRENT", "STALE")


class TestGetStaleLinks:
    """Tests for get_stale_links."""

    def test_returns_only_stale(self):
        """Only links with status=STALE are returned."""
        links_index = {
            "generated": "", "total_links": 2, "total_broken": 0, "total_errors": 0,
            "docs": {
                "doc.md": {
                    "links": [
                        {"ref": "a", "target": "a.py", "type": "file",
                         "hash": "h1", "line": 1, "status": "CURRENT"},
                        {"ref": "b", "target": "b.py", "type": "file",
                         "hash": "h2", "line": 2, "status": "STALE"},
                    ],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        stale = get_stale_links(links_index)
        assert "doc.md" in stale
        assert len(stale["doc.md"]) == 1
        assert stale["doc.md"][0]["ref"] == "b"

    def test_returns_empty_when_all_current(self):
        """All CURRENT links returns empty dict."""
        links_index = {
            "generated": "", "total_links": 1, "total_broken": 0, "total_errors": 0,
            "docs": {
                "doc.md": {
                    "links": [
                        {"ref": "a", "target": "a.py", "type": "file",
                         "hash": "h1", "line": 1, "status": "CURRENT"},
                    ],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        assert get_stale_links(links_index) == {}

    def test_returns_empty_when_no_links(self):
        """LinksIndex with no links returns empty dict."""
        links_index = {
            "generated": "", "total_links": 0, "total_broken": 0, "total_errors": 0,
            "docs": {},
        }
        assert get_stale_links(links_index) == {}


class TestGetBrokenRefs:
    """Tests for get_broken_refs."""

    def test_returns_broken(self):
        """Returns broken refs from links index."""
        links_index = {
            "generated": "", "total_links": 0, "total_broken": 1, "total_errors": 0,
            "docs": {
                "doc.md": {
                    "links": [],
                    "broken": [{"ref": "missing", "line": 5, "reason": "not found"}],
                    "errors": [],
                }
            },
        }
        broken = get_broken_refs(links_index)
        assert "doc.md" in broken
        assert len(broken["doc.md"]) == 1

    def test_returns_empty_when_no_broken(self):
        """No broken refs returns empty dict."""
        links_index = {
            "generated": "", "total_links": 1, "total_broken": 0, "total_errors": 0,
            "docs": {
                "doc.md": {
                    "links": [{"ref": "a", "target": "a.py", "type": "file",
                               "hash": "h", "line": 1}],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        assert get_broken_refs(links_index) == {}


class TestGetErrorRefs:
    """Tests for get_error_refs."""

    def test_returns_errors(self):
        """Returns error refs from links index."""
        links_index = {
            "generated": "", "total_links": 0, "total_broken": 0, "total_errors": 1,
            "docs": {
                "doc.md": {
                    "links": [],
                    "broken": [],
                    "errors": [{"ref": "helper", "line": 3,
                                "reason": "ambiguous", "candidates": ["a.py", "b.py"]}],
                }
            },
        }
        errors = get_error_refs(links_index)
        assert "doc.md" in errors
        assert len(errors["doc.md"]) == 1

    def test_returns_empty_when_no_errors(self):
        """No errors returns empty dict."""
        links_index = {
            "generated": "", "total_links": 0, "total_broken": 0, "total_errors": 0,
            "docs": {"doc.md": {"links": [], "broken": [], "errors": []}},
        }
        assert get_error_refs(links_index) == {}
