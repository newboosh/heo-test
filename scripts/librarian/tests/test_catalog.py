"""Tests for the catalog orchestrator (CLI commands)."""

import argparse
import pytest
from pathlib import Path

from scripts.librarian.catalog import (
    cmd_build,
    cmd_check,
    cmd_status,
    cmd_fix,
)
from scripts.librarian.symbol_indexer import INDEX_PATH
from scripts.librarian.resolver import LINKS_PATH


def _make_args(root=None):
    """Create a minimal argparse Namespace for CLI commands."""
    return argparse.Namespace(root=str(root) if root else None)


class TestCmdBuild:
    """Tests for cmd_build."""

    def test_build_creates_all_indexes(self, sample_markdown_docs, monkeypatch):
        """Building creates symbols.json, extracted_refs.json, and links.json."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        exit_code = cmd_build(args)
        assert exit_code == 0

        assert (root / INDEX_PATH).exists()
        assert (root / LINKS_PATH).exists()
        assert (root / "docs" / "indexes" / "extracted_refs.json").exists()

    def test_build_outputs_progress(self, sample_markdown_docs, monkeypatch, capsys):
        """Build command outputs step progress."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        cmd_build(args)
        captured = capsys.readouterr()
        assert "Step 1:" in captured.out
        assert "Step 2:" in captured.out
        assert "Step 3:" in captured.out

    def test_build_on_empty_project(self, tmp_path, monkeypatch):
        """Empty project completes without error."""
        monkeypatch.chdir(tmp_path)
        args = _make_args(root=tmp_path)
        exit_code = cmd_build(args)
        assert exit_code == 0


class TestCmdCheck:
    """Tests for cmd_check."""

    def test_check_after_build_returns_0(self, sample_markdown_docs, monkeypatch):
        """Check immediately after build returns 0 (all current)."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        cmd_build(args)

        exit_code = cmd_check(args)
        assert exit_code == 0

    def test_check_without_build_returns_1(self, tmp_path, monkeypatch, capsys):
        """Check without prior build shows error and returns 1."""
        monkeypatch.chdir(tmp_path)
        args = _make_args(root=tmp_path)
        exit_code = cmd_check(args)
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "Error" in captured.out

    def test_check_detects_stale(self, sample_markdown_docs, monkeypatch):
        """Modifying code after build causes check to detect stale."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        cmd_build(args)

        # Verify links were created
        from scripts.librarian.resolver import load_links
        links = load_links(path=root / LINKS_PATH)
        assert links is not None and links["total_links"] > 0, "Build should produce links"

        # Modify a source file
        auth = root / "app" / "services" / "auth.py"
        auth.write_text(
            "def authenticate(u, p, mfa=False):\n"
            "    return True\n"
        )

        exit_code = cmd_check(args)
        assert exit_code == 1  # stale found


class TestCmdStatus:
    """Tests for cmd_status."""

    def test_status_after_build(self, sample_markdown_docs, monkeypatch, capsys):
        """After build, status shows symbol and link counts."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        cmd_build(args)
        exit_code = cmd_status(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Symbols:" in captured.out

    def test_status_without_build(self, tmp_path, monkeypatch, capsys):
        """Without build, status shows NOT FOUND messages."""
        monkeypatch.chdir(tmp_path)
        args = _make_args(root=tmp_path)
        exit_code = cmd_status(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "NOT FOUND" in captured.out

    def test_status_always_returns_0(self, tmp_path, monkeypatch):
        """Status always returns 0 even without indexes."""
        monkeypatch.chdir(tmp_path)
        args = _make_args(root=tmp_path)
        assert cmd_status(args) == 0


class TestCmdFix:
    """Tests for cmd_fix."""

    def test_fix_without_build_returns_1(self, tmp_path, monkeypatch):
        """Fix without prior build returns 1."""
        monkeypatch.chdir(tmp_path)
        args = _make_args(root=tmp_path)
        exit_code = cmd_fix(args)
        assert exit_code == 1

    def test_fix_on_clean_build(self, sample_markdown_docs, monkeypatch):
        """Fix on a fresh build with no issues returns 0."""
        root = sample_markdown_docs
        monkeypatch.chdir(root)
        args = _make_args(root=root)
        cmd_build(args)

        exit_code = cmd_fix(args)
        assert exit_code == 0  # Fresh build should have no issues to fix
