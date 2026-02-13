"""Tests for the symbol indexer module."""

import json
import pytest
from pathlib import Path

from scripts.librarian.symbol_indexer import (
    build_symbol_index,
    save_index,
    load_index,
    get_known_symbols,
)


class TestBuildSymbolIndex:
    """Tests for build_symbol_index."""

    def test_build_from_empty_dirs(self, tmp_path):
        """Empty index_dirs yields zero symbols."""
        (tmp_path / "app").mkdir()
        index = build_symbol_index(root=tmp_path, index_dirs=["app"])
        assert index["symbol_count"] == 0
        assert index["file_count"] == 0
        assert index["symbols"] == {}

    def test_build_indexes_python_files(self, sample_python_project):
        """Python files are indexed and symbols extracted."""
        index = build_symbol_index(
            root=sample_python_project,
            index_dirs=["app", "scripts"],
        )
        assert index["symbol_count"] > 0
        assert index["file_count"] > 0
        assert "User" in index["symbols"]
        assert "authenticate" in index["symbols"]

    def test_build_skips_pycache(self, tmp_path):
        """Files in __pycache__ are skipped."""
        cache_dir = tmp_path / "app" / "__pycache__"
        cache_dir.mkdir(parents=True)
        (cache_dir / "module.cpython-39.pyc").write_text("cached")
        (cache_dir / "module.py").write_text("def should_skip(): pass\n")

        index = build_symbol_index(root=tmp_path, index_dirs=["app"])
        assert "should_skip" not in index["symbols"]

    def test_build_skips_nonexistent_dirs(self, tmp_path):
        """Non-existent directories are silently skipped."""
        index = build_symbol_index(root=tmp_path, index_dirs=["nonexistent"])
        assert index["symbol_count"] == 0

    def test_build_uses_relative_paths(self, sample_python_project):
        """Symbol file entries use paths relative to root."""
        index = build_symbol_index(
            root=sample_python_project,
            index_dirs=["app"],
        )
        for entries in index["symbols"].values():
            for entry in entries:
                assert not entry["file"].startswith("/")
                assert entry["file"].startswith("app/")

    def test_build_populates_metadata(self, sample_python_project):
        """Index has generated timestamp and counts."""
        index = build_symbol_index(
            root=sample_python_project,
            index_dirs=["app"],
        )
        assert "generated" in index
        assert isinstance(index["symbol_count"], int)
        assert isinstance(index["file_count"], int)

    def test_build_multiple_symbols_same_name(self, tmp_path):
        """Multiple files with same function name are both indexed."""
        dir_a = tmp_path / "app" / "a"
        dir_b = tmp_path / "app" / "b"
        dir_a.mkdir(parents=True)
        dir_b.mkdir(parents=True)
        (dir_a / "mod.py").write_text("def helper(): pass\n")
        (dir_b / "mod.py").write_text("def helper(): pass\n")

        index = build_symbol_index(root=tmp_path, index_dirs=["app"])
        assert "helper" in index["symbols"]
        assert len(index["symbols"]["helper"]) == 2


class TestSaveLoadIndex:
    """Tests for save_index and load_index."""

    def test_save_creates_file(self, tmp_path):
        """save_index writes a JSON file."""
        path = tmp_path / "index.json"
        index = {
            "generated": "2025-01-01",
            "symbol_count": 0,
            "file_count": 0,
            "symbols": {},
        }
        save_index(index, path=path)
        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path):
        """save_index creates intermediate directories."""
        path = tmp_path / "a" / "b" / "index.json"
        index = {
            "generated": "2025-01-01",
            "symbol_count": 0,
            "file_count": 0,
            "symbols": {},
        }
        save_index(index, path=path)
        assert path.exists()

    def test_roundtrip(self, tmp_path):
        """save then load returns equivalent data."""
        path = tmp_path / "index.json"
        index = {
            "generated": "2025-01-01T00:00:00",
            "symbol_count": 1,
            "file_count": 1,
            "symbols": {
                "func": [{"file": "mod.py", "line": 1, "type": "function", "signature": "def func()"}]
            },
        }
        save_index(index, path=path)
        loaded = load_index(path=path)
        assert loaded is not None
        assert loaded["symbol_count"] == 1
        assert "func" in loaded["symbols"]

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Loading from a missing path returns None."""
        path = tmp_path / "missing.json"
        assert load_index(path=path) is None


class TestGetKnownSymbols:
    """Tests for get_known_symbols."""

    def test_returns_symbol_names_set(self):
        """Returns a set of symbol name keys."""
        index = {
            "generated": "",
            "symbol_count": 2,
            "file_count": 1,
            "symbols": {
                "User": [{"file": "m.py", "line": 1, "type": "class", "signature": "class User"}],
                "greet": [{"file": "m.py", "line": 5, "type": "function", "signature": "def greet()"}],
            },
        }
        known = get_known_symbols(index)
        assert isinstance(known, set)
        assert known == {"User", "greet"}

    def test_empty_index_returns_empty_set(self):
        """Empty symbols dict returns empty set."""
        index = {
            "generated": "",
            "symbol_count": 0,
            "file_count": 0,
            "symbols": {},
        }
        assert get_known_symbols(index) == set()
