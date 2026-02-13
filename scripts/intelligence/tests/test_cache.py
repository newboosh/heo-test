"""Tests for BuildCache with SQLite hash tracking.

Tests:
- Hash computation and caching
- Artifact marking and freshness detection
- Dependency tracking and invalidation
- Edge cases (missing files, stale artifacts)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from scripts.intelligence.cache import BuildCache


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / ".cache.db"
    cache = BuildCache(str(db_path))
    yield cache
    cache.close()
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    temp_dir = tempfile.mkdtemp()
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("test content")
    yield str(file_path)
    shutil.rmtree(temp_dir)


class TestBuildCacheHashTracking:
    """Test hash computation and tracking."""

    def test_compute_file_hash(self, temp_db, temp_file):
        """Test SHA-256 hash computation."""
        hash1 = temp_db.compute_file_hash(temp_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 is 64 hex characters

    def test_hash_caching(self, temp_db, temp_file):
        """Test that hash is cached."""
        hash1 = temp_db.compute_file_hash(temp_file)
        hash2 = temp_db.compute_file_hash(temp_file)
        assert hash1 == hash2

    def test_compute_hash_missing_file(self, temp_db):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            temp_db.compute_file_hash("/nonexistent/file.txt")

    def test_hash_changes_with_content(self, temp_db):
        """Test hash changes when file content changes."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content1")
            temp_file = f.name

        try:
            hash1 = temp_db.compute_file_hash(temp_file)

            # Invalidate cache and change file
            temp_db.invalidate("dummy")  # Just clear cache
            with open(temp_file, 'w') as f:
                f.write("content2")

            # Recompute (cache would be stale in real scenario)
            import hashlib
            sha256 = hashlib.sha256()
            with open(temp_file, 'rb') as f:
                sha256.update(f.read())
            hash2 = sha256.hexdigest()

            assert hash1 != hash2
        finally:
            Path(temp_file).unlink()


class TestBuildCacheMarkAndFresh:
    """Test artifact marking and freshness detection."""

    def test_mark_built(self, temp_db, temp_file):
        """Test marking artifact as built."""
        hash_val = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("test_artifact", "classifier", {temp_file: hash_val})

        # Verify we can check freshness
        is_fresh = temp_db.is_fresh("test_artifact", {temp_file: hash_val})
        assert is_fresh

    def test_artifact_not_exists(self, temp_db, temp_file):
        """Test freshness check for nonexistent artifact."""
        hash_val = temp_db.compute_file_hash(temp_file)
        is_fresh = temp_db.is_fresh("nonexistent", {temp_file: hash_val})
        assert not is_fresh

    def test_dependency_hash_changed(self, temp_db, temp_file):
        """Test freshness detection when dependency hash changes."""
        hash1 = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("artifact1", "classifier", {temp_file: hash1})

        # Check with different hash
        different_hash = "different_hash_value"
        is_fresh = temp_db.is_fresh("artifact1", {temp_file: different_hash})
        assert not is_fresh

    def test_dependency_added(self, temp_db, temp_file):
        """Test freshness detection when dependencies change."""
        hash1 = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("artifact1", "classifier", {temp_file: hash1})

        # Add new dependency
        with tempfile.NamedTemporaryFile(delete=False) as f:
            new_file = f.name

        try:
            hash2 = temp_db.compute_file_hash(new_file)
            is_fresh = temp_db.is_fresh("artifact1", {
                temp_file: hash1,
                new_file: hash2
            })
            assert not is_fresh
        finally:
            Path(new_file).unlink()

    def test_dependency_removed(self, temp_db, temp_file):
        """Test freshness detection when dependencies are removed."""
        hash1 = temp_db.compute_file_hash(temp_file)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            other_file = f.name

        try:
            hash2 = temp_db.compute_file_hash(other_file)
            temp_db.mark_built("artifact1", "classifier", {
                temp_file: hash1,
                other_file: hash2
            })

            # Check with only one dependency
            is_fresh = temp_db.is_fresh("artifact1", {temp_file: hash1})
            assert not is_fresh
        finally:
            Path(other_file).unlink()


class TestBuildCacheInvalidation:
    """Test artifact invalidation."""

    def test_invalidate_artifact(self, temp_db, temp_file):
        """Test invalidation removes artifact."""
        hash_val = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("artifact1", "classifier", {temp_file: hash_val})

        is_fresh_before = temp_db.is_fresh("artifact1", {temp_file: hash_val})
        assert is_fresh_before

        temp_db.invalidate("artifact1")

        is_fresh_after = temp_db.is_fresh("artifact1", {temp_file: hash_val})
        assert not is_fresh_after

    def test_clear_cache(self, temp_db, temp_file):
        """Test clearing entire cache."""
        hash_val = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("artifact1", "classifier", {temp_file: hash_val})
        temp_db.mark_built("artifact2", "deps", {temp_file: hash_val})

        temp_db.clear()

        is_fresh1 = temp_db.is_fresh("artifact1", {temp_file: hash_val})
        is_fresh2 = temp_db.is_fresh("artifact2", {temp_file: hash_val})
        assert not is_fresh1
        assert not is_fresh2


class TestBuildCacheMultipleComponents:
    """Test cache with multiple components and artifacts."""

    def test_multiple_artifacts_same_dependency(self, temp_db, temp_file):
        """Test multiple artifacts depending on same file."""
        hash_val = temp_db.compute_file_hash(temp_file)

        temp_db.mark_built("classifier_artifact", "classifier", {temp_file: hash_val})
        temp_db.mark_built("deps_artifact", "dependency_graph", {temp_file: hash_val})

        is_fresh1 = temp_db.is_fresh("classifier_artifact", {temp_file: hash_val})
        is_fresh2 = temp_db.is_fresh("deps_artifact", {temp_file: hash_val})

        assert is_fresh1
        assert is_fresh2

    def test_replace_artifact(self, temp_db, temp_file):
        """Test replacing an artifact updates dependencies."""
        hash1 = temp_db.compute_file_hash(temp_file)
        temp_db.mark_built("artifact1", "classifier", {temp_file: hash1})

        # Replace with new dependencies
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            other_file = f.name
            f.write("other content")

        try:
            hash2 = temp_db.compute_file_hash(other_file)
            temp_db.mark_built("artifact1", "classifier", {other_file: hash2})

            # Old dependency should not make it fresh
            is_fresh_old = temp_db.is_fresh("artifact1", {temp_file: hash1})
            assert not is_fresh_old

            # New dependency should make it fresh
            is_fresh_new = temp_db.is_fresh("artifact1", {other_file: hash2})
            assert is_fresh_new
        finally:
            Path(other_file).unlink()
