"""Tests for CLI commands."""

import pytest
from pathlib import Path
import json
import yaml
import sys

from scripts.catalog.cli import main, ExitCode


class TestBuildCommand:
    """Tests for the build command."""

    def test_build_creates_output_files(self, tmp_path, monkeypatch):
        """Build command should create classification and dependencies files."""
        # Create a minimal project
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("print('hello')")

        # Create config
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["app"],
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        assert (tmp_path / "output" / "classification.json").exists()
        assert (tmp_path / "output" / "dependencies.json").exists()

    def test_build_with_defaults(self, tmp_path, monkeypatch):
        """Build without config uses defaults."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("x = 1")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build"])

        # Should succeed with defaults
        assert exit_code == ExitCode.SUCCESS

    def test_build_invalid_config_exits_1(self, tmp_path, monkeypatch):
        """Invalid config should exit with code 1."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text("{ invalid yaml: [")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build", "--config", str(config_file)])

        assert exit_code == ExitCode.CONFIG_ERROR

    def test_build_creates_state_file(self, tmp_path, monkeypatch):
        """Build should create catalog state file for incremental builds."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("x = 1")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build"])

        assert exit_code == ExitCode.SUCCESS
        # State file is now in .claude/cache/
        assert (tmp_path / ".claude" / "cache" / "catalog-state.json").exists()

    def test_build_incremental_flag(self, tmp_path, monkeypatch, capsys):
        """Build with --incremental should detect changed files."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("x = 1")

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["app"],
            "output": {"index_dir": "output"},
        }))

        monkeypatch.chdir(tmp_path)

        # First build (full)
        main(["build", "--config", str(config_file)])

        # Second build (incremental, no changes)
        exit_code = main(["build", "--incremental", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "incremental" in captured.out.lower()


class TestClassifyCommand:
    """Tests for the classify command."""

    def test_classify_creates_classification_only(self, tmp_path, monkeypatch):
        """Classify command creates only classification file."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "service.py").write_text("class Service: pass")

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["app"],
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["classify", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        assert (tmp_path / "output" / "classification.json").exists()
        # Dependencies file should NOT be created by classify
        assert not (tmp_path / "output" / "dependencies.json").exists()


class TestDepsCommand:
    """Tests for the deps command."""

    def test_deps_creates_dependencies_only(self, tmp_path, monkeypatch):
        """Deps command creates only dependencies file."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("import os")

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["app"],
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["deps", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        assert (tmp_path / "output" / "dependencies.json").exists()
        # Classification file should NOT be created by deps
        assert not (tmp_path / "output" / "classification.json").exists()


class TestQueryCommand:
    """Tests for the query command."""

    def test_query_file(self, tmp_path, monkeypatch, capsys):
        """Query specific file."""
        # Create index
        (tmp_path / "output").mkdir()
        index_file = tmp_path / "output" / "classification.json"
        index_file.write_text(json.dumps({
            "schema_version": "1.0",
            "files": {
                "app/main.py": {
                    "primary_category": "service",
                    "categories": ["service"],
                    "matched_rules": [],
                    "confidence": "high",
                }
            }
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["query", "--file", "app/main.py", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "service" in captured.out

    def test_query_category(self, tmp_path, monkeypatch, capsys):
        """Query by category."""
        (tmp_path / "output").mkdir()
        index_file = tmp_path / "output" / "classification.json"
        index_file.write_text(json.dumps({
            "schema_version": "1.0",
            "files": {
                "app/auth.py": {"primary_category": "service", "categories": ["service"], "matched_rules": [], "confidence": "high"},
                "app/user.py": {"primary_category": "service", "categories": ["service"], "matched_rules": [], "confidence": "high"},
                "tests/test.py": {"primary_category": "test", "categories": ["test"], "matched_rules": [], "confidence": "medium"},
            }
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["query", "--category", "service", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "auth.py" in captured.out
        assert "user.py" in captured.out
        assert "test.py" not in captured.out

    def test_query_depends_on(self, tmp_path, monkeypatch, capsys):
        """Query reverse dependencies."""
        (tmp_path / "output").mkdir()
        deps_file = tmp_path / "output" / "dependencies.json"
        deps_file.write_text(json.dumps({
            "schema_version": "1.0",
            "modules": {
                "app/model.py": {
                    "imports": [],
                    "imported_by": ["app/service.py", "tests/test_model.py"],
                    "external": [],
                }
            }
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["query", "--depends-on", "app/model.py", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "service.py" in captured.out
        assert "test_model.py" in captured.out

    def test_query_imports(self, tmp_path, monkeypatch, capsys):
        """Query forward dependencies (what does a file import)."""
        (tmp_path / "output").mkdir()
        deps_file = tmp_path / "output" / "dependencies.json"
        deps_file.write_text(json.dumps({
            "schema_version": "1.0",
            "modules": {
                "app/service.py": {
                    "imports": ["app/model.py", "app/utils.py"],
                    "imported_by": [],
                    "external": ["flask"],
                }
            }
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["query", "--imports", "app/service.py", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "app/model.py" in captured.out
        assert "app/utils.py" in captured.out
        assert "[external] flask" in captured.out

    def test_query_summary(self, tmp_path, monkeypatch, capsys):
        """Query summary returns stats without full data."""
        (tmp_path / "output").mkdir()
        index_file = tmp_path / "output" / "classification.json"
        index_file.write_text(json.dumps({
            "schema_version": "1.0",
            "generated": "2026-01-31T14:30:00Z",
            "file_count": 25,
            "by_category": {"service": 10, "test": 15},
            "files": {},
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["query", "--summary", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "25" in captured.out  # file_count
        assert "service" in captured.out
        assert "test" in captured.out


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_shows_index_info(self, tmp_path, monkeypatch, capsys):
        """Status command shows index information."""
        (tmp_path / "output").mkdir()

        class_file = tmp_path / "output" / "classification.json"
        class_file.write_text(json.dumps({
            "schema_version": "1.0",
            "generated": "2026-01-31T14:30:00Z",
            "file_count": 10,
            "by_category": {"service": 5, "test": 3, "model": 2},
            "files": {},
        }))

        deps_file = tmp_path / "output" / "dependencies.json"
        deps_file.write_text(json.dumps({
            "schema_version": "1.0",
            "generated": "2026-01-31T14:30:00Z",
            "module_count": 8,
            "modules": {},
        }))

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
                "dependencies_file": "dependencies.json",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["status", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "10" in captured.out  # file count
        assert "service" in captured.out
        assert "test" in captured.out

    def test_status_missing_indexes(self, tmp_path, monkeypatch, capsys):
        """Status shows message when indexes don't exist."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["status"])

        # Should succeed but indicate no indexes
        assert exit_code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "missing" in captured.out.lower() or "no" in captured.out.lower()


class TestExitCodes:
    """Tests for exit codes."""

    def test_success_exit_code(self, tmp_path, monkeypatch):
        """Successful build returns 0."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build"])

        assert exit_code == ExitCode.SUCCESS
        assert exit_code == 0

    def test_config_error_exit_code(self, tmp_path, monkeypatch):
        """Invalid config returns 1."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text("not: valid: yaml: [[[")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build", "--config", str(config_file)])

        assert exit_code == ExitCode.CONFIG_ERROR
        assert exit_code == 1

    def test_partial_success_exit_code_value(self):
        """PARTIAL_SUCCESS exit code should be 3."""
        assert ExitCode.PARTIAL_SUCCESS == 3


class TestPartialSuccess:
    """Tests for PARTIAL_SUCCESS exit code (3) when files are skipped."""

    def test_build_returns_partial_success_on_circular_symlink(self, tmp_path, monkeypatch, capsys):
        """Build should return exit code 3 when circular symlinks are skipped."""
        # Create a config
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "follow_symlinks": True,
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
                "dependencies_file": "dependencies.json",
            },
        }))

        # Create a directory structure with a circular symlink
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.py").write_text("x = 1")

        # Create circular symlink: subdir/loop -> subdir
        loop_link = subdir / "loop"
        try:
            loop_link.symlink_to(subdir, target_is_directory=True)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build", "--config", str(config_file)])

        # Should succeed but with partial success due to skipped circular symlink
        assert exit_code == ExitCode.PARTIAL_SUCCESS
        assert exit_code == 3
        captured = capsys.readouterr()
        # Should mention skipped files
        assert "skipped" in captured.out.lower() or "circular" in captured.err.lower()

    def test_classify_returns_partial_success_on_circular_symlink(self, tmp_path, monkeypatch, capsys):
        """Classify should return exit code 3 when circular symlinks are skipped."""
        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["."],
            "follow_symlinks": True,
            "output": {
                "index_dir": "output",
                "classification_file": "classification.json",
            },
        }))

        # Create a directory structure with a circular symlink
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.py").write_text("x = 1")

        # Create circular symlink
        loop_link = subdir / "loop"
        try:
            loop_link.symlink_to(subdir, target_is_directory=True)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["classify", "--config", str(config_file)])

        assert exit_code == ExitCode.PARTIAL_SUCCESS
        assert exit_code == 3

    def test_build_returns_success_without_skipped_files(self, tmp_path, monkeypatch):
        """Build should return exit code 0 when no files are skipped."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("print('hello')")

        config_file = tmp_path / "catalog.yaml"
        config_file.write_text(yaml.dump({
            "version": "1.0",
            "index_dirs": ["app"],
            "output": {
                "index_dir": "output",
            },
        }))

        monkeypatch.chdir(tmp_path)
        exit_code = main(["build", "--config", str(config_file)])

        assert exit_code == ExitCode.SUCCESS
        assert exit_code == 0


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_directory_structure(self, tmp_path, monkeypatch):
        """Init should create .claude/catalog directories."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["init"])

        assert exit_code == ExitCode.SUCCESS
        assert (tmp_path / ".claude" / "catalog").is_dir()
        assert (tmp_path / ".claude" / "catalog" / "indexes").is_dir()
        assert (tmp_path / ".claude" / "cache").is_dir()

    def test_init_creates_config_file(self, tmp_path, monkeypatch):
        """Init should create a config file."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["init"])

        assert exit_code == ExitCode.SUCCESS
        config_path = tmp_path / ".claude" / "catalog" / "config.yaml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "version:" in content

    def test_init_updates_gitignore(self, tmp_path, monkeypatch):
        """Init should add cache directory to .gitignore."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["init"])

        assert exit_code == ExitCode.SUCCESS
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        assert ".claude/cache/" in gitignore.read_text()

    def test_init_preserves_existing_config(self, tmp_path, monkeypatch, capsys):
        """Init should not overwrite existing config."""
        (tmp_path / ".claude" / "catalog").mkdir(parents=True)
        config_path = tmp_path / ".claude" / "catalog" / "config.yaml"
        config_path.write_text("# My custom config")

        monkeypatch.chdir(tmp_path)
        exit_code = main(["init"])

        assert exit_code == ExitCode.SUCCESS
        assert config_path.read_text() == "# My custom config"
        captured = capsys.readouterr()
        assert "already exists" in captured.out

