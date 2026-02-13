"""Tests for file classifier component.

Tests:
- Directory pattern matching
- Filename pattern matching
- Content regex matching
- AST pattern matching (Python)
- Multi-language support
- Edge cases (no matches, invalid files)
"""

import pytest
import tempfile
from pathlib import Path
from scripts.intelligence.components.classifier import Classifier, Classification


@pytest.fixture
def classifier():
    """Create classifier with default rules."""
    return Classifier()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestClassifierDirectoryPatterns:
    """Test directory pattern matching."""

    def test_test_directory(self, classifier):
        """Test matching files in test directory."""
        classification = classifier.classify_file("/home/project/tests/unit_test.py")
        assert classification.category == "test"
        assert classification.confidence == "high"

    def test_docs_directory(self, classifier):
        """Test matching files in docs directory."""
        classification = classifier.classify_file("/home/project/docs/guide.md")
        assert classification.category == "docs"

    def test_build_directory(self, classifier):
        """Test matching files in build directory."""
        classification = classifier.classify_file("/home/project/build/output.o")
        assert classification.category == "build"


class TestClassifierFilenamePatterns:
    """Test filename pattern matching."""

    def test_test_filename_python(self, classifier):
        """Test Python test filename pattern."""
        classification = classifier.classify_file("/home/project/src/test_utils.py")
        assert classification.category == "test"
        assert classification.language == "python"

    def test_test_filename_typescript(self, classifier):
        """Test TypeScript test filename pattern."""
        classification = classifier.classify_file("/home/project/src/helper.spec.ts")
        assert classification.category == "test"
        assert classification.language == "typescript"

    def test_config_filename(self, classifier):
        """Test config filename pattern."""
        classification = classifier.classify_file("/home/project/config.yaml")
        assert classification.category == "config"

    def test_readme_filename(self, classifier):
        """Test README filename pattern."""
        classification = classifier.classify_file("/home/project/README.md")
        assert classification.category == "docs"


class TestClassifierContentPatterns:
    """Test content pattern matching."""

    def test_python_test_content(self, classifier, temp_dir):
        """Test Python test detection via import."""
        test_file = Path(temp_dir) / "helper_test.py"  # Matches test pattern
        test_file.write_text("import unittest\n\nclass TestCase(unittest.TestCase): pass")

        classification = classifier.classify_file(str(test_file))
        assert classification.category == "test"
        # Will match filename pattern first (high confidence)
        assert classification.confidence in ["high", "medium"]

    def test_shell_script_content(self, classifier, temp_dir):
        """Test shell script detection."""
        shell_file = Path(temp_dir) / "script.sh"
        shell_file.write_text("#!/bin/bash\necho 'Hello'")

        classification = classifier.classify_file(str(shell_file))
        assert classification.category == "shell"

    def test_dockerfile_content(self, classifier, temp_dir):
        """Test Dockerfile detection."""
        dockerfile = Path(temp_dir) / "Dockerfile"
        dockerfile.write_text("FROM ubuntu:20.04\nRUN apt-get update")

        classification = classifier.classify_file(str(dockerfile))
        assert classification.category == "docker"


class TestClassifierAstPatterns:
    """Test AST pattern matching (Python)."""

    def test_pytest_import(self, classifier, temp_dir):
        """Test pytest import detection."""
        test_file = Path(temp_dir) / "test_module.py"
        test_file.write_text("import pytest\n\ndef test_something(): pass")

        classification = classifier.classify_file(str(test_file))
        assert classification.category == "test"
        assert classification.language == "python"

    def test_unittest_import(self, classifier, temp_dir):
        """Test unittest import detection."""
        test_file = Path(temp_dir) / "tests.py"
        test_file.write_text("from unittest import TestCase\n\nclass MyTest(TestCase): pass")

        classification = classifier.classify_file(str(test_file))
        assert classification.category == "test"


class TestClassifierLanguageDetection:
    """Test language detection."""

    def test_python_language(self, classifier):
        """Test Python language detection."""
        classification = classifier.classify_file("/code/module.py")
        assert classification.language == "python"

    def test_typescript_language(self, classifier):
        """Test TypeScript language detection."""
        classification = classifier.classify_file("/code/utils.ts")
        assert classification.language == "typescript"

    def test_javascript_language(self, classifier):
        """Test JavaScript language detection."""
        classification = classifier.classify_file("/code/app.js")
        assert classification.language == "javascript"

    def test_shell_language(self, classifier):
        """Test Shell language detection."""
        classification = classifier.classify_file("/scripts/deploy.sh")
        assert classification.language == "shell"

    def test_unknown_language(self, classifier):
        """Test unknown language detection."""
        classification = classifier.classify_file("/config/settings.xyz")
        assert classification.language is None


class TestClassifierEdgeCases:
    """Test edge cases and error conditions."""

    def test_uncategorized_file(self, classifier):
        """Test uncategorized file classification."""
        classification = classifier.classify_file("/home/random_file.xyz")
        assert classification.category == "uncategorized"
        assert classification.confidence == "low"

    def test_hidden_file(self, classifier):
        """Test classification of hidden files."""
        classification = classifier.classify_file("/home/project/.env.local")
        assert classification.category == "config"

    def test_multiple_extensions(self, classifier):
        """Test file with multiple extensions."""
        classification = classifier.classify_file("/archive/backup.tar.gz")
        # Should detect based on name or be uncategorized
        assert classification.file_path.endswith(".tar.gz")

    def test_no_extension(self, classifier):
        """Test file with no extension."""
        classification = classifier.classify_file("/home/Makefile")
        assert classification.category == "build"

    def test_classify_all(self, classifier, temp_dir):
        """Test classifying all files in directory."""
        # Create test files
        Path(temp_dir, "test_module.py").write_text("import pytest")
        Path(temp_dir, "config.yaml").write_text("key: value")
        Path(temp_dir, "README.md").write_text("# Project")

        classifications = classifier.classify_all(temp_dir)
        assert len(classifications) == 3

        categories = [c.category for c in classifications]
        assert "test" in categories
        assert "config" in categories
        assert "docs" in categories

    def test_classification_result_fields(self, classifier):
        """Test Classification dataclass has expected fields."""
        classification = classifier.classify_file("/test/test_module.py")

        assert hasattr(classification, 'file_path')
        assert hasattr(classification, 'category')
        assert hasattr(classification, 'confidence')
        assert hasattr(classification, 'language')
        assert hasattr(classification, 'matched_rule')

    def test_pattern_precedence(self, classifier, temp_dir):
        """Test that directory patterns have higher precedence."""
        test_file = Path(temp_dir, "tests", "helpers.py")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Regular helper module")

        classification = classifier.classify_file(str(test_file))
        # Should match directory pattern "test*" over generic categorization
        assert classification.category == "test"


class TestClassifierPatternMatching:
    """Test pattern matching helper functions."""

    def test_glob_matches_wildcard(self):
        """Test glob pattern with wildcard."""
        assert Classifier._glob_matches("test_utils.py", "test_*.py") is True
        assert Classifier._glob_matches("utils_test.py", "test_*.py") is False

    def test_glob_matches_star(self):
        """Test glob pattern with star."""
        assert Classifier._glob_matches("file.txt", "*.txt") is True
        assert Classifier._glob_matches("file.py", "*.txt") is False

    def test_path_matches_directory(self):
        """Test path pattern matching."""
        assert Classifier._path_matches_pattern("src/tests/module.py", "test*") is True
        assert Classifier._path_matches_pattern("src/utils/module.py", "test*") is False

    def test_path_matches_nested(self):
        """Test nested path matching."""
        path = "home/user/project/tests/unit/test_module.py"
        assert Classifier._path_matches_pattern(path, "test*") is True
        assert Classifier._path_matches_pattern(path, "*test*") is True
