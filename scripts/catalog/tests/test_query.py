"""Tests for query interface."""

import pytest
from pathlib import Path
import json

from scripts.catalog.query import (
    query_by_category,
    query_by_file,
    query_depends_on,
    query_imports,
    get_summary,
    load_classification_index,
    load_dependencies_index,
)


@pytest.fixture
def sample_classification(tmp_path):
    """Create a sample classification index."""
    index_file = tmp_path / "file_classification.json"
    index_data = {
        "schema_version": "1.0",
        "generated": "2026-01-31T14:30:00Z",
        "file_count": 5,
        "by_category": {"service": 2, "test": 2, "model": 1},
        "files": {
            "app/services/auth.py": {
                "primary_category": "service",
                "categories": ["service"],
                "matched_rules": ["directory:app/services/**"],
                "confidence": "high",
            },
            "app/services/user.py": {
                "primary_category": "service",
                "categories": ["service"],
                "matched_rules": ["directory:app/services/**"],
                "confidence": "high",
            },
            "app/models/user.py": {
                "primary_category": "model",
                "categories": ["model"],
                "matched_rules": ["ast_content:class_inherits:BaseModel"],
                "confidence": "high",
            },
            "tests/test_auth.py": {
                "primary_category": "test",
                "categories": ["test"],
                "matched_rules": ["filename:test_*.py"],
                "confidence": "medium",
            },
            "tests/test_user.py": {
                "primary_category": "test",
                "categories": ["test"],
                "matched_rules": ["filename:test_*.py"],
                "confidence": "medium",
            },
        },
    }
    index_file.write_text(json.dumps(index_data, indent=2))
    return index_file


@pytest.fixture
def sample_dependencies(tmp_path):
    """Create a sample dependencies index."""
    index_file = tmp_path / "module_dependencies.json"
    index_data = {
        "schema_version": "1.0",
        "generated": "2026-01-31T14:30:00Z",
        "module_count": 3,
        "modules": {
            "app/services/auth.py": {
                "imports": ["app/models/user.py"],
                "imported_by": ["tests/test_auth.py"],
                "external": ["flask", "jwt"],
            },
            "app/models/user.py": {
                "imports": [],
                "imported_by": ["app/services/auth.py", "app/services/user.py"],
                "external": ["pydantic"],
            },
            "tests/test_auth.py": {
                "imports": ["app/services/auth.py"],
                "imported_by": [],
                "external": ["pytest"],
            },
        },
    }
    index_file.write_text(json.dumps(index_data, indent=2))
    return index_file


class TestQueryByCategory:
    """Tests for category-based queries."""

    def test_query_single_category(self, sample_classification):
        """Query files in a single category."""
        index = load_classification_index(sample_classification)
        results = query_by_category(index, "service")

        assert len(results) == 2
        file_paths = [r["file_path"] for r in results]
        assert "app/services/auth.py" in file_paths
        assert "app/services/user.py" in file_paths

    def test_query_category_returns_full_info(self, sample_classification):
        """Query should return full file classification info."""
        index = load_classification_index(sample_classification)
        results = query_by_category(index, "test")

        assert len(results) == 2
        for r in results:
            assert "file_path" in r
            assert "primary_category" in r
            assert "categories" in r
            assert "confidence" in r

    def test_query_nonexistent_category(self, sample_classification):
        """Query for non-existent category returns empty list."""
        index = load_classification_index(sample_classification)
        results = query_by_category(index, "nonexistent")

        assert results == []


class TestQueryByFile:
    """Tests for file-based queries."""

    def test_query_existing_file(self, sample_classification):
        """Query specific file returns its classification."""
        index = load_classification_index(sample_classification)
        result = query_by_file(index, "app/services/auth.py")

        assert result is not None
        assert result["primary_category"] == "service"
        assert result["confidence"] == "high"

    def test_query_nonexistent_file(self, sample_classification):
        """Query for non-existent file returns None."""
        index = load_classification_index(sample_classification)
        result = query_by_file(index, "nonexistent.py")

        assert result is None


class TestQueryDependsOn:
    """Tests for reverse dependency queries."""

    def test_query_depends_on(self, sample_dependencies):
        """Query what files import a given file."""
        index = load_dependencies_index(sample_dependencies)
        results = query_depends_on(index, "app/models/user.py")

        assert len(results) == 2
        assert "app/services/auth.py" in results
        assert "app/services/user.py" in results

    def test_query_depends_on_leaf_file(self, sample_dependencies):
        """Query file with no dependents returns empty list."""
        index = load_dependencies_index(sample_dependencies)
        results = query_depends_on(index, "tests/test_auth.py")

        assert results == []

    def test_query_depends_on_nonexistent(self, sample_dependencies):
        """Query non-existent file returns empty list."""
        index = load_dependencies_index(sample_dependencies)
        results = query_depends_on(index, "nonexistent.py")

        assert results == []


class TestQueryImports:
    """Tests for forward dependency queries."""

    def test_query_imports(self, sample_dependencies):
        """Query what a file imports."""
        index = load_dependencies_index(sample_dependencies)
        result = query_imports(index, "app/services/auth.py")

        assert result is not None
        assert "app/models/user.py" in result["imports"]
        assert "flask" in result["external"]
        assert "jwt" in result["external"]

    def test_query_imports_file_with_no_imports(self, sample_dependencies):
        """Query file with no imports returns empty lists."""
        index = load_dependencies_index(sample_dependencies)
        result = query_imports(index, "app/models/user.py")

        assert result is not None
        assert result["imports"] == []
        assert "pydantic" in result["external"]


class TestGetSummary:
    """Tests for summary statistics."""

    def test_classification_summary(self, sample_classification):
        """Get summary of classification index."""
        index = load_classification_index(sample_classification)
        summary = get_summary(index)

        assert summary["file_count"] == 5
        assert summary["by_category"]["service"] == 2
        assert summary["by_category"]["test"] == 2
        assert summary["by_category"]["model"] == 1

    def test_summary_includes_generated_timestamp(self, sample_classification):
        """Summary should include generation timestamp."""
        index = load_classification_index(sample_classification)
        summary = get_summary(index)

        assert "generated" in summary


class TestLoadIndexes:
    """Tests for index loading."""

    def test_load_missing_file_returns_none(self, tmp_path):
        """Loading missing index file returns None."""
        result = load_classification_index(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        """Loading invalid JSON returns None."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ invalid json }")

        result = load_classification_index(bad_file)
        assert result is None

    def test_load_valid_index(self, sample_classification):
        """Loading valid index returns data."""
        index = load_classification_index(sample_classification)

        assert index is not None
        assert "files" in index
        assert "schema_version" in index
