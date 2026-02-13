"""Tests for the reference extractor module."""

import pytest
from pathlib import Path

from scripts.librarian.reference_extractor import (
    extract_all_references,
    save_refs,
    load_refs,
)


class TestExtractAllReferences:
    """Tests for extract_all_references."""

    def test_extract_from_single_doc(self, sample_markdown_docs, sample_known_symbols):
        """Extract references from a single markdown file."""
        refs = extract_all_references(
            root=sample_markdown_docs,
            doc_dirs=["docs"],
            known_symbols=sample_known_symbols,
        )
        assert refs["ref_count"] > 0
        assert refs["doc_count"] > 0

    def test_extract_from_multiple_docs(self, sample_markdown_docs, sample_known_symbols):
        """Multiple markdown files are all scanned."""
        refs = extract_all_references(
            root=sample_markdown_docs,
            doc_dirs=["docs"],
            known_symbols=sample_known_symbols,
        )
        # api.md and architecture.md both have refs
        assert refs["doc_count"] == 2

    def test_skips_indexes_directory(self, sample_markdown_docs, sample_known_symbols):
        """Files in docs/indexes/ are skipped."""
        refs = extract_all_references(
            root=sample_markdown_docs,
            doc_dirs=["docs"],
            known_symbols=sample_known_symbols,
        )
        doc_paths = list(refs["docs"].keys())
        for path in doc_paths:
            assert "indexes" not in path

    def test_empty_docs_dir(self, tmp_path):
        """Empty docs directory yields zero refs."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        refs = extract_all_references(
            root=tmp_path,
            doc_dirs=["docs"],
            known_symbols=set(),
        )
        assert refs["ref_count"] == 0
        assert refs["doc_count"] == 0

    def test_nonexistent_doc_dir_skipped(self, tmp_path):
        """Non-existent doc_dirs entry is silently skipped."""
        refs = extract_all_references(
            root=tmp_path,
            doc_dirs=["nonexistent"],
            known_symbols=set(),
        )
        assert refs["ref_count"] == 0

    def test_custom_doc_dirs(self, tmp_path):
        """Custom doc_dirs override the default."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "readme.md").write_text("See `app/main.py` for entry.\n")

        refs = extract_all_references(
            root=tmp_path,
            doc_dirs=["notes"],
            known_symbols=set(),
        )
        assert refs["ref_count"] == 1

    def test_populates_metadata(self, sample_markdown_docs, sample_known_symbols):
        """Check generated, doc_count, ref_count fields."""
        refs = extract_all_references(
            root=sample_markdown_docs,
            doc_dirs=["docs"],
            known_symbols=sample_known_symbols,
        )
        assert "generated" in refs
        assert isinstance(refs["doc_count"], int)
        assert isinstance(refs["ref_count"], int)


class TestSaveLoadRefs:
    """Tests for save_refs and load_refs."""

    def test_roundtrip(self, tmp_path):
        """Save then load returns equivalent data."""
        path = tmp_path / "refs.json"
        refs = {
            "generated": "2025-01-01",
            "doc_count": 1,
            "ref_count": 1,
            "docs": {
                "docs/api.md": [{"text": "User", "type": "symbol", "line": 5}]
            },
        }
        save_refs(refs, path=path)
        loaded = load_refs(path=path)
        assert loaded is not None
        assert loaded["ref_count"] == 1
        assert "docs/api.md" in loaded["docs"]

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Loading from missing path returns None."""
        path = tmp_path / "missing.json"
        assert load_refs(path=path) is None
