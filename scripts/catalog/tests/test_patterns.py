"""Tests for pattern matching utilities."""

import pytest
from pathlib import Path
import tempfile

from scripts.catalog.patterns import (
    match_directory_pattern,
    match_filename_pattern,
    match_content_pattern,
    get_confidence_for_match,
)


class TestDirectoryPatternMatching:
    """Tests for glob-based directory pattern matching."""

    def test_match_simple_directory(self):
        """Match files in a specific directory."""
        assert match_directory_pattern("app/services/auth.py", "app/services/**")
        assert match_directory_pattern("app/services/nested/deep.py", "app/services/**")
        assert not match_directory_pattern("app/models/user.py", "app/services/**")

    def test_match_directory_with_star(self):
        """Match using single-star patterns."""
        assert match_directory_pattern("tests/test_auth.py", "tests/*")
        assert not match_directory_pattern("tests/unit/test_auth.py", "tests/*")

    def test_match_double_star_anywhere(self):
        """Match ** for any depth."""
        assert match_directory_pattern("app/utils/helpers.py", "**/utils/**")
        assert match_directory_pattern("src/lib/utils/string.py", "**/utils/**")
        assert match_directory_pattern("utils/common.py", "**/utils/**")

    def test_match_exact_directory(self):
        """Match exact directory path."""
        assert match_directory_pattern("migrations/001_init.py", "migrations/**")
        assert not match_directory_pattern("app/migrations/001.py", "migrations/**")

    def test_relative_path_handling(self):
        """Paths should be relative to project root."""
        assert match_directory_pattern("./app/services/auth.py", "app/services/**")
        assert match_directory_pattern("app/services/auth.py", "./app/services/**")


class TestFilenamePatternMatching:
    """Tests for filename pattern matching."""

    def test_match_prefix_pattern(self):
        """Match filename prefix patterns."""
        assert match_filename_pattern("test_auth.py", "test_*.py")
        assert match_filename_pattern("test_models_user.py", "test_*.py")
        assert not match_filename_pattern("auth_test.py", "test_*.py")

    def test_match_suffix_pattern(self):
        """Match filename suffix patterns."""
        assert match_filename_pattern("auth.test.ts", "*.test.ts")
        assert match_filename_pattern("user.test.ts", "*.test.ts")
        assert not match_filename_pattern("test_auth.ts", "*.test.ts")

    def test_match_extension_pattern(self):
        """Match by file extension."""
        assert match_filename_pattern("config.json", "*.json")
        assert match_filename_pattern("settings.config.json", "*.config.json")

    def test_match_exact_filename(self):
        """Match exact filename."""
        assert match_filename_pattern("Dockerfile", "Dockerfile")
        assert match_filename_pattern("Dockerfile", "Dockerfile*")
        assert match_filename_pattern("Dockerfile.prod", "Dockerfile*")

    def test_match_dotfile_pattern(self):
        """Match dotfile patterns."""
        assert match_filename_pattern(".env", ".env*")
        assert match_filename_pattern(".env.local", ".env*")
        assert match_filename_pattern(".env.production", ".env*")

    def test_match_docker_compose_variants(self):
        """Match docker-compose file variants."""
        assert match_filename_pattern("docker-compose.yml", "docker-compose*.yml")
        assert match_filename_pattern("docker-compose.prod.yml", "docker-compose*.yml")
        assert match_filename_pattern("docker-compose-dev.yml", "docker-compose*.yml")

    def test_case_sensitivity(self):
        """Filename matching should be case-sensitive on case-sensitive systems."""
        # The pattern should match exactly
        assert match_filename_pattern("Test_auth.py", "Test_*.py")
        # This may vary by platform, but pattern should be literal


class TestContentPatternMatching:
    """Tests for regex-based content pattern matching."""

    def test_match_simple_regex(self, tmp_path):
        """Match simple regex in file content."""
        test_file = tmp_path / "widget.dart"
        test_file.write_text("class MyWidget extends StatefulWidget {}")
        assert match_content_pattern(test_file, r"extends.*Widget")

    def test_match_with_filetypes_restriction(self, tmp_path):
        """Match content only in specified filetypes."""
        dart_file = tmp_path / "widget.dart"
        dart_file.write_text("extends Widget")

        py_file = tmp_path / "widget.py"
        py_file.write_text("extends Widget")  # Same content

        # Should match only .dart files
        assert match_content_pattern(dart_file, r"extends.*Widget", filetypes=[".dart"])
        assert not match_content_pattern(py_file, r"extends.*Widget", filetypes=[".dart"])

    def test_match_no_filetypes_matches_all(self, tmp_path):
        """When filetypes is None, match any text file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("CREATE TABLE users")
        assert match_content_pattern(py_file, r"CREATE TABLE")

    def test_match_typescript_test_patterns(self, tmp_path):
        """Match test patterns in TypeScript files."""
        test_file = tmp_path / "auth.test.ts"
        test_file.write_text("""
        describe('auth', () => {
            it('should login', () => {
                expect(true).toBe(true);
            });
        });
        """)
        assert match_content_pattern(test_file, r"describe\(|it\(|test\(", filetypes=[".ts", ".js"])

    def test_match_react_patterns(self, tmp_path):
        """Match React patterns in TSX files."""
        component = tmp_path / "Button.tsx"
        component.write_text("""
        import React from 'react';
        const Button: React.FC = () => <button>Click</button>;
        """)
        assert match_content_pattern(component, r"React\.FC|useState|useEffect", filetypes=[".tsx", ".jsx"])

    def test_no_match_binary_file(self, tmp_path):
        """Binary files should not be matched."""
        binary_file = tmp_path / "image.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
        # Should return False gracefully, not crash
        assert not match_content_pattern(binary_file, r"anything")

    def test_no_match_encoding_error(self, tmp_path):
        """Files with encoding errors should be handled gracefully."""
        bad_file = tmp_path / "bad.txt"
        bad_file.write_bytes(b'\xff\xfe invalid utf-8 \x80\x81')
        # Should return False, not crash
        assert not match_content_pattern(bad_file, r"anything")


class TestConfidenceLevels:
    """Tests for confidence level assignment."""

    def test_directory_match_high_confidence(self):
        """Directory pattern matches should be high confidence."""
        conf = get_confidence_for_match("directory", "app/services/**")
        assert conf == "high"

    def test_filename_match_medium_confidence(self):
        """Filename pattern matches should be medium confidence."""
        conf = get_confidence_for_match("filename", "test_*.py")
        assert conf == "medium"

    def test_content_match_varies(self):
        """Content pattern confidence varies by specificity."""
        # Simple patterns are low confidence
        conf_simple = get_confidence_for_match("content", r"import")
        assert conf_simple in ("low", "medium")

        # More specific patterns are higher confidence
        conf_specific = get_confidence_for_match("content", r"extends.*StatefulWidget")
        assert conf_specific in ("medium", "high")

    def test_ast_content_high_confidence(self):
        """AST content matches should be high confidence."""
        conf = get_confidence_for_match("ast_content", "class_inherits:BaseModel")
        assert conf == "high"
