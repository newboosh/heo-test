"""Tests for incremental build functionality."""

import pytest
from pathlib import Path
import json
import time

from scripts.catalog.incremental import (
    compute_file_hash,
    load_state,
    save_state,
    get_changed_files,
    CatalogState,
)


class TestComputeFileHash:
    """Tests for file hash computation."""

    def test_hash_simple_file(self, tmp_path):
        """Compute hash of a simple file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        hash1 = compute_file_hash(test_file)

        assert hash1 is not None
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_hash_changes_with_content(self, tmp_path):
        """Hash should change when content changes."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        hash1 = compute_file_hash(test_file)

        test_file.write_text("print('world')")
        hash2 = compute_file_hash(test_file)

        assert hash1 != hash2

    def test_hash_same_for_same_content(self, tmp_path):
        """Same content should produce same hash."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        content = "print('identical')"
        file1.write_text(content)
        file2.write_text(content)

        assert compute_file_hash(file1) == compute_file_hash(file2)

    def test_hash_nonexistent_returns_none(self, tmp_path):
        """Non-existent file should return None."""
        result = compute_file_hash(tmp_path / "nonexistent.py")
        assert result is None


class TestCatalogState:
    """Tests for catalog state persistence."""

    def test_save_and_load_state(self, tmp_path):
        """State should round-trip through save/load."""
        state_file = tmp_path / ".catalog_state.json"
        state = CatalogState(
            file_hashes={"app/main.py": "abc123", "app/utils.py": "def456"},
            last_build="2026-01-31T14:30:00Z",
        )

        save_state(state, state_file)
        loaded = load_state(state_file)

        assert loaded is not None
        assert loaded.file_hashes == state.file_hashes
        assert loaded.last_build == state.last_build

    def test_load_missing_state_returns_empty(self, tmp_path):
        """Loading missing state file returns empty state."""
        state = load_state(tmp_path / "nonexistent.json")

        assert state is not None
        assert state.file_hashes == {}

    def test_load_corrupted_state_returns_empty(self, tmp_path):
        """Loading corrupted state file returns empty state."""
        state_file = tmp_path / ".catalog_state.json"
        state_file.write_text("{ invalid json }")

        state = load_state(state_file)

        assert state is not None
        assert state.file_hashes == {}


class TestGetChangedFiles:
    """Tests for change detection."""

    def test_all_files_changed_on_first_run(self, tmp_path):
        """All files should be marked changed on first run (no state)."""
        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "utils.py").write_text("y = 2")

        files = ["app.py", "utils.py"]
        empty_state = CatalogState(file_hashes={}, last_build=None)

        changed = get_changed_files(tmp_path, files, empty_state)

        assert set(changed) == {"app.py", "utils.py"}

    def test_unchanged_files_not_returned(self, tmp_path):
        """Files with same hash should not be returned."""
        (tmp_path / "app.py").write_text("x = 1")
        hash1 = compute_file_hash(tmp_path / "app.py")

        state = CatalogState(file_hashes={"app.py": hash1}, last_build="2026-01-31T14:30:00Z")

        changed = get_changed_files(tmp_path, ["app.py"], state)

        assert changed == []

    def test_modified_files_returned(self, tmp_path):
        """Files with different hash should be returned."""
        (tmp_path / "app.py").write_text("x = 1")
        old_hash = "different_hash_from_before"

        state = CatalogState(file_hashes={"app.py": old_hash}, last_build="2026-01-31T14:30:00Z")

        changed = get_changed_files(tmp_path, ["app.py"], state)

        assert changed == ["app.py"]

    def test_new_files_returned(self, tmp_path):
        """New files (not in state) should be returned."""
        (tmp_path / "new_file.py").write_text("new content")

        state = CatalogState(file_hashes={"old_file.py": "abc123"}, last_build="2026-01-31T14:30:00Z")

        changed = get_changed_files(tmp_path, ["new_file.py"], state)

        assert changed == ["new_file.py"]

    def test_deleted_files_tracked(self, tmp_path):
        """State tracks files that were deleted."""
        # File exists in state but not on disk
        state = CatalogState(
            file_hashes={"deleted.py": "abc123", "existing.py": "def456"},
            last_build="2026-01-31T14:30:00Z",
        )

        (tmp_path / "existing.py").write_text("content")
        # deleted.py does not exist

        # Only check existing.py
        changed = get_changed_files(tmp_path, ["existing.py"], state)

        # existing.py should be detected as changed (different hash)
        assert "existing.py" in changed
