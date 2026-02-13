"""Tests for utility modules.

Tests for ast_utils, file_utils, hash_utils, json_utils.
"""

import pytest
import tempfile
import json
from pathlib import Path
from scripts.intelligence.utils import ast_utils, file_utils, hash_utils, json_utils


class TestAstUtils:
    """Test AST utilities."""

    def test_parse_python_file(self):
        """Test parsing valid Python file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello(): pass")
            f.flush()
            try:
                tree = ast_utils.parse_python_file(f.name)
                assert tree is not None
                assert isinstance(tree, ast_utils.ast.Module)
            finally:
                Path(f.name).unlink()

    def test_parse_invalid_python(self):
        """Test parsing invalid Python returns None."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def invalid( ")  # Syntax error
            f.flush()
            try:
                tree = ast_utils.parse_python_file(f.name)
                assert tree is None
            finally:
                Path(f.name).unlink()

    def test_get_function_defs(self):
        """Test extracting function definitions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def func1(): pass
def func2(): pass
class MyClass: pass
""")
            f.flush()
            try:
                tree = ast_utils.parse_python_file(f.name)
                funcs = ast_utils.get_function_defs(tree)
                assert len(funcs) == 2
                assert funcs[0].name == "func1"
                assert funcs[1].name == "func2"
            finally:
                Path(f.name).unlink()

    def test_get_class_defs(self):
        """Test extracting class definitions."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class Class1: pass
def func(): pass
class Class2: pass
""")
            f.flush()
            try:
                tree = ast_utils.parse_python_file(f.name)
                classes = ast_utils.get_class_defs(tree)
                assert len(classes) == 2
                assert classes[0].name == "Class1"
                assert classes[1].name == "Class2"
            finally:
                Path(f.name).unlink()


class TestFileUtils:
    """Test file utilities."""

    def test_read_file(self):
        """Test reading file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            try:
                content = file_utils.read_file(f.name)
                assert content == "test content"
            finally:
                Path(f.name).unlink()

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file returns None."""
        content = file_utils.read_file("/nonexistent/file.txt")
        assert content is None

    def test_write_file(self):
        """Test writing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "subdir" / "test.txt"
            result = file_utils.write_file(str(file_path), "content")
            assert result is True
            assert file_path.exists()
            assert file_path.read_text() == "content"

    def test_iterate_files(self):
        """Test iterating files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "file1.py").write_text("code1")
            Path(tmpdir, "file2.py").write_text("code2")
            Path(tmpdir, "file3.txt").write_text("data")

            files = list(file_utils.iterate_files(tmpdir, extensions={'.py'}))
            assert len(files) == 2
            assert all(f.endswith('.py') for f in files)

    def test_get_python_files(self):
        """Test getting Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("code")
            Path(tmpdir, "util.py").write_text("code")
            Path(tmpdir, "data.json").write_text("{}")

            files = list(file_utils.get_python_files(tmpdir))
            assert len(files) == 2
            assert all(f.endswith('.py') for f in files)

    def test_file_size(self):
        """Test getting file size."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content")
            f.flush()
            try:
                size = file_utils.file_size(f.name)
                assert size == 7
            finally:
                Path(f.name).unlink()

    def test_file_exists(self):
        """Test file existence check."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                assert file_utils.file_exists(f.name) is True
                assert file_utils.file_exists("/nonexistent/file") is False
            finally:
                Path(f.name).unlink()


class TestHashUtils:
    """Test hashing utilities."""

    def test_compute_file_hash(self):
        """Test file hashing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            try:
                hash1 = hash_utils.compute_file_hash(f.name)
                assert hash1 is not None
                assert len(hash1) == 64  # SHA-256 hex is 64 chars
            finally:
                Path(f.name).unlink()

    def test_hash_consistency(self):
        """Test same content gives same hash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            try:
                hash1 = hash_utils.compute_file_hash(f.name)
                hash2 = hash_utils.compute_file_hash(f.name)
                assert hash1 == hash2
            finally:
                Path(f.name).unlink()

    def test_hash_differs_with_content(self):
        """Test different content gives different hash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("content1")
            f1.flush()
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
                f2.write("content2")
                f2.flush()
                try:
                    hash1 = hash_utils.compute_file_hash(f1.name)
                    hash2 = hash_utils.compute_file_hash(f2.name)
                    assert hash1 != hash2
                finally:
                    Path(f1.name).unlink()
                    Path(f2.name).unlink()

    def test_compute_string_hash(self):
        """Test string hashing."""
        hash1 = hash_utils.compute_string_hash("test")
        assert len(hash1) == 64

    def test_verify_hash(self):
        """Test hash verification."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content")
            f.flush()
            try:
                actual_hash = hash_utils.compute_file_hash(f.name)
                assert hash_utils.verify_hash(f.name, actual_hash) is True
                assert hash_utils.verify_hash(f.name, "wronghash") is False
            finally:
                Path(f.name).unlink()


class TestJsonUtils:
    """Test JSON utilities."""

    def test_dumps_basic(self):
        """Test basic JSON serialization."""
        data = {"key": "value", "number": 42}
        json_str = json_utils.dumps(data, pretty=False)
        assert json.loads(json_str) == data

    def test_dumps_pretty(self):
        """Test pretty JSON serialization."""
        data = {"key": "value"}
        json_str = json_utils.dumps(data, pretty=True)
        assert "\n" in json_str  # Should have newlines

    def test_dumps_path(self):
        """Test serializing Path objects."""
        data = {"path": Path("/some/path")}
        json_str = json_utils.dumps(data)
        result = json.loads(json_str)
        assert result["path"] == "/some/path"

    def test_dumps_set(self):
        """Test serializing sets."""
        data = {"items": {1, 2, 3}}
        json_str = json_utils.dumps(data)
        result = json.loads(json_str)
        assert sorted(result["items"]) == [1, 2, 3]

    def test_loads(self):
        """Test JSON deserialization."""
        json_str = '{"key": "value"}'
        data = json_utils.loads(json_str)
        assert data == {"key": "value"}

    def test_dump_and_load_file(self):
        """Test file I/O."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "data.json"
            data = {"test": "value", "number": 42}

            # Write
            result = json_utils.dump_file(str(file_path), data)
            assert result is True
            assert file_path.exists()

            # Load
            loaded = json_utils.load_file(str(file_path))
            assert loaded == data

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file returns None."""
        data = json_utils.load_file("/nonexistent/file.json")
        assert data is None

    def test_merge_dicts(self):
        """Test dictionary merging."""
        d1 = {"a": 1, "b": {"c": 2}}
        d2 = {"b": {"d": 3}, "e": 4}
        result = json_utils.merge_dicts(d1, d2)
        assert result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

    def test_filter_dict(self):
        """Test dictionary filtering."""
        data = {"a": 1, "b": 2, "c": 3}
        result = json_utils.filter_dict(data, ["a", "c"])
        assert result == {"a": 1, "c": 3}
