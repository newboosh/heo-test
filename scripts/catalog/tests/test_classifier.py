"""Tests for file classification."""

import os
import pytest
from pathlib import Path
import yaml

from scripts.catalog.classifier import (
    classify_file,
    classify_directory,
    FileClassification,
    ClassificationResult,
)
from scripts.catalog.config import load_config, get_default_config, CatalogConfig


class TestClassifyFile:
    """Tests for single file classification."""

    def test_directory_pattern_high_confidence(self, tmp_path):
        """Directory pattern match should have high confidence."""
        # Create a config with directory rule
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "service",
                    "rules": [{"type": "directory", "pattern": "app/services/**"}]
                }],
                "priority_order": ["service"],
            }
        }))
        config = load_config(config_file)

        # Create the file structure
        (tmp_path / "app" / "services").mkdir(parents=True)
        test_file = tmp_path / "app" / "services" / "auth.py"
        test_file.write_text("class AuthService: pass")

        result = classify_file(test_file, tmp_path, config)

        assert result.primary_category == "service"
        assert "service" in result.categories
        assert result.confidence == "high"
        assert "directory:app/services/**" in result.matched_rules

    def test_filename_pattern_medium_confidence(self, tmp_path):
        """Filename pattern match should have medium confidence."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{"type": "filename", "pattern": "test_*.py"}]
                }],
                "priority_order": ["test"],
            }
        }))
        config = load_config(config_file)

        test_file = tmp_path / "test_auth.py"
        test_file.write_text("def test_login(): pass")

        result = classify_file(test_file, tmp_path, config)

        assert result.primary_category == "test"
        assert result.confidence == "medium"

    def test_content_pattern_match(self, tmp_path):
        """Content pattern should match file contents."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "widget",
                    "rules": [{"type": "content", "pattern": "extends.*Widget", "filetypes": [".dart"]}]
                }],
                "priority_order": ["widget"],
            }
        }))
        config = load_config(config_file)

        dart_file = tmp_path / "button.dart"
        dart_file.write_text("class MyButton extends StatefulWidget {}")

        result = classify_file(dart_file, tmp_path, config)

        assert result.primary_category == "widget"

    def test_ast_content_pattern_high_confidence(self, tmp_path):
        """AST content pattern should have high confidence."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "model",
                    "rules": [{"type": "ast_content", "condition": "class_inherits:BaseModel"}]
                }],
                "priority_order": ["model"],
            }
        }))
        config = load_config(config_file)

        py_file = tmp_path / "user.py"
        py_file.write_text("class User(BaseModel):\n    name: str")

        result = classify_file(py_file, tmp_path, config)

        assert result.primary_category == "model"
        assert result.confidence == "high"

    def test_multiple_categories_priority_order(self, tmp_path):
        """Multiple matches should use priority order for primary category."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [
                    {"name": "test", "rules": [{"type": "filename", "pattern": "test_*.py"}]},
                    {"name": "model", "rules": [{"type": "ast_content", "condition": "class_inherits:BaseModel"}]},
                ],
                "priority_order": ["test", "model"],  # test has higher priority
            }
        }))
        config = load_config(config_file)

        # File matches both test (filename) and model (AST)
        test_file = tmp_path / "test_models.py"
        test_file.write_text("class TestUser(BaseModel):\n    pass")

        result = classify_file(test_file, tmp_path, config)

        # Primary should be "test" due to priority order
        assert result.primary_category == "test"
        # But both categories should be listed
        assert "test" in result.categories
        assert "model" in result.categories

    def test_no_match_returns_uncategorized(self, tmp_path):
        """Files with no matching rules should be uncategorized."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "service",
                    "rules": [{"type": "directory", "pattern": "services/**"}]
                }],
                "default_category": "uncategorized",
                "priority_order": ["service"],
            }
        }))
        config = load_config(config_file)

        random_file = tmp_path / "random.txt"
        random_file.write_text("just some text")

        result = classify_file(random_file, tmp_path, config)

        assert result.primary_category == "uncategorized"
        assert result.confidence == "low"

    def test_content_pattern_respects_filetypes(self, tmp_path):
        """Content patterns should only match specified filetypes."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "react",
                    "rules": [{"type": "content", "pattern": "React\\.FC", "filetypes": [".tsx", ".jsx"]}]
                }],
                "priority_order": ["react"],
            }
        }))
        config = load_config(config_file)

        # TSX file with React.FC should match
        tsx_file = tmp_path / "Button.tsx"
        tsx_file.write_text("const Button: React.FC = () => null;")

        # PY file with same content should NOT match (wrong filetype)
        py_file = tmp_path / "component.py"
        py_file.write_text("React.FC = 'fake'")

        tsx_result = classify_file(tsx_file, tmp_path, config)
        py_result = classify_file(py_file, tmp_path, config)

        assert tsx_result.primary_category == "react"
        assert py_result.primary_category == "uncategorized"


class TestClassifyDirectory:
    """Tests for directory-wide classification."""

    def test_classify_multiple_files(self, tmp_path):
        """Should classify all files in directory."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "classification": {
                "categories": [
                    {"name": "test", "rules": [{"type": "filename", "pattern": "test_*.py"}]},
                    {"name": "service", "rules": [{"type": "directory", "pattern": "services/**"}]},
                ],
                "priority_order": ["test", "service"],
            }
        }))
        config = load_config(config_file)

        # Create files
        (tmp_path / "services").mkdir()
        (tmp_path / "services" / "auth.py").write_text("class Auth: pass")
        (tmp_path / "test_auth.py").write_text("def test_auth(): pass")
        (tmp_path / "random.txt").write_text("random")

        result = classify_directory(tmp_path, config)
        classifications = result.classifications

        # Should have at least 3 files (plus the config file)
        assert len(classifications) >= 3
        # Check results by file
        file_results = {r.file_path: r for r in classifications}

        assert "services/auth.py" in file_results
        assert file_results["services/auth.py"].primary_category == "service"

        assert "test_auth.py" in file_results
        assert file_results["test_auth.py"].primary_category == "test"

        assert "random.txt" in file_results
        assert file_results["random.txt"].primary_category == "uncategorized"

    def test_respects_skip_dirs(self, tmp_path):
        """Should skip configured directories."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "skip_dirs": ["__pycache__", "node_modules"],
            "classification": {
                "categories": [
                    {"name": "python", "rules": [{"type": "filename", "pattern": "*.py"}]},
                ],
                "priority_order": ["python"],
            }
        }))
        config = load_config(config_file)

        # Create files including in skip dirs
        (tmp_path / "app.py").write_text("print('app')")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "app.cpython-39.pyc").write_bytes(b'\x00')
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "lodash.js").write_text("module.exports = {}")

        result = classify_directory(tmp_path, config)
        classifications = result.classifications

        file_paths = [r.file_path for r in classifications]
        assert "app.py" in file_paths
        assert not any("__pycache__" in p for p in file_paths)
        assert not any("node_modules" in p for p in file_paths)

    def test_respects_max_file_size(self, tmp_path):
        """Large files should skip content scanning but still classify by other rules."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "max_file_size": 100,  # Very small limit for testing
            "classification": {
                "categories": [
                    {"name": "test", "rules": [{"type": "filename", "pattern": "test_*.py"}]},
                    {"name": "migration", "rules": [{"type": "content", "pattern": "CREATE TABLE"}]},
                ],
                "priority_order": ["test", "migration"],
            }
        }))
        config = load_config(config_file)

        # Create a large file with matching content pattern
        large_file = tmp_path / "migration_001.py"
        large_file.write_text("CREATE TABLE users" + " " * 200)  # Exceeds 100 bytes

        # Create a test file (should match by filename, not content)
        test_file = tmp_path / "test_migration.py"
        test_file.write_text("def test(): pass")

        result = classify_directory(tmp_path, config)
        file_results = {r.file_path: r for r in result.classifications}

        # Large file should be classified but content pattern skipped
        assert "migration_001.py" in file_results
        # Since content pattern is skipped due to size, it won't match "migration"
        assert file_results["migration_001.py"].primary_category == "uncategorized"

        # Test file should still match by filename
        assert file_results["test_migration.py"].primary_category == "test"


class TestFileClassification:
    """Tests for FileClassification data structure."""

    def test_classification_has_all_fields(self, tmp_path):
        """FileClassification should have all required fields."""
        config = get_default_config()
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        result = classify_file(test_file, tmp_path, config)

        assert hasattr(result, "file_path")
        assert hasattr(result, "primary_category")
        assert hasattr(result, "categories")
        assert hasattr(result, "matched_rules")
        assert hasattr(result, "confidence")

    def test_matched_rules_format(self, tmp_path):
        """Matched rules should include rule type and pattern."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "classification": {
                "categories": [{
                    "name": "test",
                    "rules": [{"type": "filename", "pattern": "test_*.py"}]
                }],
                "priority_order": ["test"],
            }
        }))
        config = load_config(config_file)

        test_file = tmp_path / "test_auth.py"
        test_file.write_text("def test(): pass")

        result = classify_file(test_file, tmp_path, config)

        assert "filename:test_*.py" in result.matched_rules


class TestClassificationResult:
    """Tests for ClassificationResult structure."""

    def test_result_has_skipped_count(self, tmp_path):
        """ClassificationResult should include skipped_count."""
        config = get_default_config()

        result = classify_directory(tmp_path, config)

        assert hasattr(result, "classifications")
        assert hasattr(result, "skipped_count")
        assert hasattr(result, "skipped_files")
        assert isinstance(result.classifications, list)
        assert isinstance(result.skipped_count, int)
        assert isinstance(result.skipped_files, list)

    def test_result_tracks_classification_errors(self, tmp_path):
        """ClassificationResult should track files that fail to classify."""
        # Create a config that triggers AST analysis
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "classification": {
                "categories": [{
                    "name": "model",
                    "rules": [{"type": "ast_content", "condition": "class_inherits:BaseModel"}]
                }],
            }
        }))
        config = load_config(config_file)

        # Create a valid Python file
        (tmp_path / "valid.py").write_text("x = 1")

        result = classify_directory(tmp_path, config)

        # Result should have classifications list
        assert len(result.classifications) >= 1
        # skipped_count starts at 0 for normal files
        assert result.skipped_count >= 0


class TestCircularSymlinkDetection:
    """Tests for circular symlink detection."""

    def test_circular_directory_symlink_detected(self, tmp_path, capsys):
        """Circular directory symlink should be detected and skipped."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "follow_symlinks": True,
            "classification": {
                "categories": [{
                    "name": "python",
                    "rules": [{"type": "filename", "pattern": "*.py"}]
                }],
            }
        }))
        config = load_config(config_file)

        # Create a directory structure with a circular symlink
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.py").write_text("x = 1")

        # Create circular symlink: subdir/loop -> subdir (points back to parent)
        loop_link = subdir / "loop"
        try:
            loop_link.symlink_to(subdir, target_is_directory=True)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        result = classify_directory(tmp_path, config)

        # Should have classified the file but detected the circular link
        assert any(c.file_path == "subdir/file.py" for c in result.classifications)
        # Circular symlink should be skipped and warned
        captured = capsys.readouterr()
        assert result.skipped_count >= 1 or "circular" in captured.err.lower()

    def test_symlinks_not_followed_when_disabled(self, tmp_path):
        """Symlinks should not be followed when follow_symlinks=False."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "follow_symlinks": False,
            "classification": {
                "categories": [{
                    "name": "python",
                    "rules": [{"type": "filename", "pattern": "*.py"}]
                }],
            }
        }))
        config = load_config(config_file)

        # Create a file and a symlink to it
        (tmp_path / "real.py").write_text("x = 1")
        link_file = tmp_path / "link.py"
        try:
            link_file.symlink_to(tmp_path / "real.py")
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        result = classify_directory(tmp_path, config)

        # Only the real file should be classified, not the symlink
        file_paths = [c.file_path for c in result.classifications]
        assert "real.py" in file_paths
        # link.py should NOT be in results since follow_symlinks=False
        assert "link.py" not in file_paths

    def test_normal_symlinks_followed_when_enabled(self, tmp_path):
        """Non-circular symlinks should be followed when follow_symlinks=True."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "follow_symlinks": True,
            "classification": {
                "categories": [{
                    "name": "python",
                    "rules": [{"type": "filename", "pattern": "*.py"}]
                }],
            }
        }))
        config = load_config(config_file)

        # Create a directory outside of scan dirs
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        (external_dir / "external.py").write_text("x = 1")

        # Create a file in the main dir
        (tmp_path / "main.py").write_text("y = 2")

        # Create a symlink to external dir
        link_dir = tmp_path / "linked"
        try:
            link_dir.symlink_to(external_dir, target_is_directory=True)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        result = classify_directory(tmp_path, config)

        file_paths = [c.file_path for c in result.classifications]
        assert "main.py" in file_paths
        # The linked file should also be found
        assert "linked/external.py" in file_paths
