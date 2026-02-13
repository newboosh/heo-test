"""End-to-end pipeline tests for the full librarian system."""

import json
import pytest
from pathlib import Path

from scripts.librarian.symbol_indexer import build_symbol_index, save_index, load_index, INDEX_PATH
from scripts.librarian.reference_extractor import extract_all_references, save_refs, REFS_PATH
from scripts.librarian.resolver import resolve_all_references, save_links, load_links, LINKS_PATH
from scripts.librarian.checker import check_all_links
from scripts.librarian.fixer import gather_fix_context, save_fix_report


class TestEndToEndPipeline:
    """Full pipeline tests exercising build → check → fix flow."""

    def _run_build(self, root, monkeypatch):
        """Run the complete build pipeline."""
        monkeypatch.chdir(root)

        # Step 1: Build symbol index
        index = build_symbol_index(root=root, index_dirs=["app", "scripts"])
        save_index(index, path=root / INDEX_PATH)

        # Step 2: Extract references
        known = set(index["symbols"].keys())
        refs = extract_all_references(root, known_symbols=known)
        save_refs(refs, path=root / REFS_PATH)

        # Step 3: Resolve
        links = resolve_all_references(root, index)
        save_links(links, path=root / LINKS_PATH)

        return index, refs, links

    def test_full_pipeline_clean_project(self, sample_markdown_docs, monkeypatch):
        """Fresh build on clean project: all links current, 0 broken."""
        root = sample_markdown_docs
        _index, _refs, links = self._run_build(root, monkeypatch)

        # Check all links
        assert links["total_links"] > 0, "Fixture should produce links"
        _updated_links, report = check_all_links(root, links)
        assert report["stale"] == 0
        assert report["current"] == report["total_checked"]

    def test_full_pipeline_with_stale_refs(self, sample_markdown_docs, monkeypatch):
        """Build, modify code, detect staleness."""
        root = sample_markdown_docs
        _, _, links = self._run_build(root, monkeypatch)

        assert links["total_links"] > 0, "Fixture should produce links"

        # Modify source code
        auth_file = root / "app" / "services" / "auth.py"
        auth_file.write_text(
            "def authenticate(user, password, two_factor=False):\n"
            "    return True\n"
        )

        _, report = check_all_links(root, links)
        assert report["stale"] > 0

    def test_full_pipeline_with_broken_refs(self, sample_markdown_docs, monkeypatch):
        """Build, delete referenced file, detect broken refs on rebuild."""
        root = sample_markdown_docs
        _index, _refs, _links = self._run_build(root, monkeypatch)

        # Delete a source file that's referenced
        auth_file = root / "app" / "services" / "auth.py"
        if auth_file.exists():
            auth_file.unlink()

        # Rebuild - broken refs should appear
        index2 = build_symbol_index(root=root, index_dirs=["app", "scripts"])
        save_index(index2, path=root / INDEX_PATH)

        known2 = set(index2["symbols"].keys())
        refs2 = extract_all_references(root, known_symbols=known2)
        save_refs(refs2, path=root / REFS_PATH)

        links2 = resolve_all_references(root, index2)
        # File refs to deleted file should be broken
        # (symbol refs might also be broken since authenticate is gone)
        total_broken = links2["total_broken"]
        # Docs reference auth.py directly, so deleting it should create broken refs
        assert total_broken > 0

    def test_pipeline_idempotent(self, sample_markdown_docs, monkeypatch):
        """Running build twice produces equivalent results."""
        root = sample_markdown_docs
        _, _, links1 = self._run_build(root, monkeypatch)

        _, _, links2 = self._run_build(root, monkeypatch)

        assert links1["total_links"] == links2["total_links"]
        assert links1["total_broken"] == links2["total_broken"]
        assert links1["total_errors"] == links2["total_errors"]

    def test_pipeline_handles_empty_project(self, tmp_path, monkeypatch):
        """Project with no Python or Markdown files completes gracefully."""
        monkeypatch.chdir(tmp_path)

        index = build_symbol_index(root=tmp_path, index_dirs=["app"])
        save_index(index, path=tmp_path / INDEX_PATH)
        assert index["symbol_count"] == 0

        refs = extract_all_references(root=tmp_path, known_symbols=set())
        save_refs(refs, path=tmp_path / REFS_PATH)
        assert refs["ref_count"] == 0

        links = resolve_all_references(tmp_path, index)
        assert links["total_links"] == 0

    def test_pipeline_json_roundtrip(self, sample_markdown_docs, monkeypatch):
        """All JSON files written can be loaded back successfully."""
        root = sample_markdown_docs
        self._run_build(root, monkeypatch)

        # All index files should be valid JSON that can be loaded
        loaded_index = load_index(path=root / INDEX_PATH)
        assert loaded_index is not None
        assert "symbols" in loaded_index

        loaded_links = load_links(path=root / LINKS_PATH)
        assert loaded_links is not None
        assert "docs" in loaded_links

        # Extracted refs too
        refs_path = root / REFS_PATH
        assert refs_path.exists()
        refs_data = json.loads(refs_path.read_text())
        assert "docs" in refs_data

    def test_fix_report_generation(self, sample_markdown_docs, monkeypatch):
        """Full flow through to fix report with prompts."""
        root = sample_markdown_docs
        _, _, links = self._run_build(root, monkeypatch)

        # Modify code to create staleness
        auth_file = root / "app" / "services" / "auth.py"
        auth_file.write_text(
            "def authenticate(u, p):\n    return False\n"
        )

        # Check and then fix
        updated_links, _report = check_all_links(root, links)
        fix_report = gather_fix_context(root, updated_links)

        assert isinstance(fix_report["total_issues"], int)
        assert fix_report["total_issues"] == fix_report["stale"] + fix_report["broken"] + fix_report["errors"]

        # Save should work
        fix_path = root / "docs" / "indexes" / "fix_report.json"
        save_fix_report(fix_report, path=fix_path)
        assert fix_path.exists()
