"""Tests for the reference resolver module."""

import pytest
from pathlib import Path

from scripts.librarian.resolver import (
    resolve_all_references,
    save_links,
    load_links,
    _resolve_file_ref,
    _resolve_symbol_ref,
    _resolve_import_ref,
    _resolve_single_ref,
)
from scripts.librarian.symbol_indexer import (
    build_symbol_index,
    save_index,
    INDEX_PATH,
)
from scripts.librarian.reference_extractor import (
    extract_all_references,
    save_refs,
    REFS_PATH,
)


class TestResolveFileRef:
    """Tests for file reference resolution."""

    def test_resolve_existing_file(self, sample_python_project):
        """File ref to a real file resolves with a hash."""
        result = _resolve_file_ref("app/models/user.py", 10, sample_python_project)
        assert "hash" in result
        assert result["type"] == "file"
        assert result["target"] == "app/models/user.py"

    def test_resolve_missing_file(self, sample_python_project):
        """File ref to non-existent file returns broken ref."""
        result = _resolve_file_ref("app/missing.py", 10, sample_python_project)
        assert "reason" in result
        assert "hash" not in result

    def test_resolved_file_has_line(self, sample_python_project):
        """Resolved file ref preserves the line number."""
        result = _resolve_file_ref("app/models/user.py", 42, sample_python_project)
        assert result["line"] == 42


class TestResolveSymbolRef:
    """Tests for symbol reference resolution."""

    def test_resolve_unique_symbol(self, sample_python_project, sample_symbol_index):
        """Symbol with a single definition resolves correctly."""
        result = _resolve_symbol_ref(
            "authenticate", 5, sample_python_project, sample_symbol_index,
        )
        assert "hash" in result
        assert "auth" in result["target"]

    def test_resolve_ambiguous_symbol(self, tmp_path):
        """Symbol with multiple definitions returns ErrorRef with candidates."""
        # Create two files with the same function name
        dir_a = tmp_path / "app" / "a"
        dir_b = tmp_path / "app" / "b"
        dir_a.mkdir(parents=True)
        dir_b.mkdir(parents=True)
        (dir_a / "mod.py").write_text("def helper(): pass\n")
        (dir_b / "mod.py").write_text("def helper(): pass\n")

        index = build_symbol_index(root=tmp_path, index_dirs=["app"])
        result = _resolve_symbol_ref("helper", 1, tmp_path, index)
        assert "candidates" in result
        assert len(result["candidates"]) == 2

    def test_resolve_nonexistent_symbol(self, sample_python_project, sample_symbol_index):
        """Unknown symbol returns broken ref."""
        result = _resolve_symbol_ref(
            "nonexistent_func", 5, sample_python_project, sample_symbol_index,
        )
        assert "reason" in result
        assert "not found" in result["reason"]

    def test_resolve_symbol_strips_parentheses(self, sample_python_project, sample_symbol_index):
        """Trailing () is stripped from symbol names."""
        result = _resolve_symbol_ref(
            "authenticate()", 5, sample_python_project, sample_symbol_index,
        )
        assert "hash" in result

    def test_resolve_qualified_symbol(self, sample_python_project, sample_symbol_index):
        """Qualified name resolves via path matching."""
        result = _resolve_symbol_ref(
            "app.services.auth.authenticate", 5, sample_python_project, sample_symbol_index,
        )
        assert "hash" in result
        assert "auth" in result["target"]


class TestResolveImportRef:
    """Tests for import reference resolution."""

    def test_resolve_from_import(self, sample_python_project, sample_symbol_index):
        """from X import Y resolves to module file."""
        result = _resolve_import_ref(
            "from app.services.auth import authenticate",
            10,
            sample_python_project,
            sample_symbol_index,
        )
        assert "hash" in result
        assert result["type"] == "file"

    def test_resolve_direct_import(self, sample_python_project, sample_symbol_index):
        """import X resolves to module file."""
        result = _resolve_import_ref(
            "import app.services.auth",
            10,
            sample_python_project,
            sample_symbol_index,
        )
        assert "hash" in result

    def test_resolve_missing_module(self, sample_python_project, sample_symbol_index):
        """Non-existent module returns broken ref."""
        result = _resolve_import_ref(
            "from app.nonexistent import thing",
            10,
            sample_python_project,
            sample_symbol_index,
        )
        assert "reason" in result
        assert "not found" in result["reason"]

    def test_resolve_package_init(self, sample_python_project, sample_symbol_index):
        """Package (with __init__.py) resolves correctly."""
        result = _resolve_import_ref(
            "import app.models",
            10,
            sample_python_project,
            sample_symbol_index,
        )
        # app/models/__init__.py exists
        assert "hash" in result


class TestResolveSingleRef:
    """Tests for the _resolve_single_ref dispatcher."""

    def test_unknown_ref_type_returns_error(self, sample_python_project, sample_symbol_index):
        """Unknown ref_type returns an error dict with reason."""
        result = _resolve_single_ref(
            "something", "unknown_type", 1, sample_python_project, sample_symbol_index,
        )
        assert "reason" in result
        assert "unknown ref type" in result["reason"]


class TestResolveAllReferences:
    """Tests for the full resolve_all_references pipeline."""

    def _build_links(self, root, index, monkeypatch):
        """Build the full pipeline and return the links index."""
        save_index(index, path=root / INDEX_PATH)
        known = set(index["symbols"].keys())
        refs = extract_all_references(root, known_symbols=known)
        save_refs(refs, path=root / REFS_PATH)
        monkeypatch.chdir(root)
        return resolve_all_references(root, index)

    def test_full_pipeline(self, sample_markdown_docs, sample_symbol_index, monkeypatch):
        """Build index, extract refs, resolve all; verify LinksIndex structure."""
        root = sample_markdown_docs
        links = self._build_links(root, sample_symbol_index, monkeypatch)

        assert "generated" in links
        assert "total_links" in links
        assert "total_broken" in links
        assert "total_errors" in links
        assert "docs" in links
        assert links["total_links"] > 0

    def test_metadata_populated(self, sample_markdown_docs, sample_symbol_index, monkeypatch):
        """LinksIndex metadata fields are properly set."""
        root = sample_markdown_docs
        links = self._build_links(root, sample_symbol_index, monkeypatch)

        assert isinstance(links["total_links"], int)
        assert isinstance(links["total_broken"], int)
        assert isinstance(links["total_errors"], int)
        total = links["total_links"] + links["total_broken"] + links["total_errors"]
        # Total should match sum of all refs across docs
        doc_total = sum(
            len(d["links"]) + len(d["broken"]) + len(d["errors"])
            for d in links["docs"].values()
        )
        assert total == doc_total


class TestSaveLoadLinks:
    """Tests for save_links and load_links."""

    def test_roundtrip(self, tmp_path):
        """Save then load returns equivalent data."""
        path = tmp_path / "links.json"
        links = {
            "generated": "2025-01-01",
            "total_links": 1,
            "total_broken": 0,
            "total_errors": 0,
            "docs": {
                "docs/api.md": {
                    "links": [
                        {"ref": "User", "target": "app/models/user.py::User",
                         "type": "class", "hash": "abc123", "line": 5}
                    ],
                    "broken": [],
                    "errors": [],
                }
            },
        }
        save_links(links, path=path)
        loaded = load_links(path=path)
        assert loaded is not None
        assert loaded["total_links"] == 1

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Loading from missing path returns None."""
        path = tmp_path / "missing.json"
        assert load_links(path=path) is None
