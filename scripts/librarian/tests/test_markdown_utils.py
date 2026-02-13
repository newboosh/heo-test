"""Tests for markdown reference extraction utilities."""

import pytest
from pathlib import Path

from scripts.librarian.utils.markdown_utils import (
    extract_references_from_markdown,
    is_internal_reference,
    find_doc_section_for_ref,
)


class TestExtractReferencesFromMarkdown:
    """Tests for extract_references_from_markdown."""

    def test_extract_backtick_file_reference(self, tmp_path):
        """Backticked file path extracts as type=file."""
        md = tmp_path / "doc.md"
        md.write_text("See `app/models/user.py` for details.\n")
        refs = extract_references_from_markdown(str(md))
        assert len(refs) == 1
        assert refs[0]["text"] == "app/models/user.py"
        assert refs[0]["type"] == "file"

    def test_extract_backtick_symbol_reference(self, tmp_path):
        """Backticked symbol with known_symbols extracts as type=symbol."""
        md = tmp_path / "doc.md"
        md.write_text("The `User` class is important.\n")
        refs = extract_references_from_markdown(str(md), known_symbols={"User"})
        assert len(refs) == 1
        assert refs[0]["text"] == "User"
        assert refs[0]["type"] == "symbol"

    def test_extract_qualified_symbol(self, tmp_path):
        """Qualified name like app.services.auth.authenticate extracts as symbol."""
        md = tmp_path / "doc.md"
        md.write_text("Call `app.services.auth.authenticate` to log in.\n")
        refs = extract_references_from_markdown(str(md))
        assert len(refs) == 1
        assert refs[0]["type"] == "symbol"

    def test_extract_import_from_fenced_block(self, tmp_path):
        """Import statements in fenced code blocks extract as type=import."""
        md = tmp_path / "doc.md"
        md.write_text(
            "Example:\n"
            "\n"
            "```python\n"
            "from app.services.auth import authenticate\n"
            "```\n"
        )
        refs = extract_references_from_markdown(str(md))
        import_refs = [r for r in refs if r["type"] == "import"]
        assert len(import_refs) == 1
        assert "from app.services.auth" in import_refs[0]["text"]

    def test_deduplication_same_ref_same_line(self, tmp_path):
        """Same text on same line is not duplicated."""
        md = tmp_path / "doc.md"
        # This shouldn't happen in practice, but tests dedup logic
        md.write_text("Use `app/models/user.py` and also `app/models/user.py`.\n")
        refs = extract_references_from_markdown(str(md))
        file_refs = [r for r in refs if r["text"] == "app/models/user.py"]
        # Both are on the same line - regex finds both matches but dedup removes second
        assert len(file_refs) == 1

    def test_unknown_symbol_not_extracted(self, tmp_path):
        """Unknown backticked text that is not a file path is not extracted."""
        md = tmp_path / "doc.md"
        md.write_text("Use `random_thing` for something.\n")
        refs = extract_references_from_markdown(str(md), known_symbols=set())
        assert len(refs) == 0

    def test_nonexistent_file_returns_empty(self):
        """Missing markdown file returns empty list."""
        refs = extract_references_from_markdown("/nonexistent/doc.md")
        assert refs == []

    def test_empty_file_returns_empty(self, tmp_path):
        """Empty markdown file returns empty list."""
        md = tmp_path / "empty.md"
        md.write_text("")
        refs = extract_references_from_markdown(str(md))
        assert refs == []

    def test_line_numbers_are_correct(self, tmp_path):
        """Verify line numbers match actual markdown lines."""
        md = tmp_path / "doc.md"
        md.write_text(
            "# Title\n"
            "\n"
            "First paragraph.\n"
            "\n"
            "See `app/models/user.py` here.\n"
        )
        refs = extract_references_from_markdown(str(md))
        assert len(refs) == 1
        assert refs[0]["line"] == 5

    def test_known_symbols_none_handled(self, tmp_path):
        """Passing known_symbols=None does not crash."""
        md = tmp_path / "doc.md"
        md.write_text("The `app/models/user.py` file.\n")
        refs = extract_references_from_markdown(str(md), known_symbols=None)
        assert len(refs) >= 1

    def test_multiple_refs_on_different_lines(self, tmp_path):
        """Multiple references across lines are all extracted."""
        md = tmp_path / "doc.md"
        md.write_text(
            "See `app/models/user.py` for models.\n"
            "And `scripts/utils/helper.py` for utils.\n"
        )
        refs = extract_references_from_markdown(str(md))
        assert len(refs) == 2


class TestIsInternalReference:
    """Tests for is_internal_reference."""

    def test_app_path_is_internal(self):
        """app/ paths are internal."""
        assert is_internal_reference("app/services/auth.py")

    def test_scripts_path_is_internal(self):
        """scripts/ paths are internal."""
        assert is_internal_reference("scripts/catalog/config.py")

    def test_import_from_app_is_internal(self):
        """Import from app module is internal."""
        assert is_internal_reference("from app.services import auth")

    def test_external_module_not_internal(self):
        """External module name is not internal."""
        assert not is_internal_reference("numpy")

    def test_known_symbol_is_internal(self):
        """Symbol in known_symbols is internal."""
        assert is_internal_reference("User", known_symbols={"User"})

    def test_symbol_with_parens_is_internal(self):
        """Symbol with trailing () is internal if base name is known."""
        assert is_internal_reference("authenticate()", known_symbols={"authenticate"})


class TestFindDocSectionForRef:
    """Tests for find_doc_section_for_ref."""

    def test_finds_nearest_header(self, tmp_path):
        """Find the nearest header above a reference line."""
        md = tmp_path / "doc.md"
        md.write_text(
            "# Title\n"
            "\n"
            "## API Section\n"
            "\n"
            "Some text about the API.\n"
            "\n"
            "Reference on this line.\n"
        )
        section = find_doc_section_for_ref(str(md), 7)
        assert section == "API Section"

    def test_no_header_returns_none(self, tmp_path):
        """File with no headers returns None."""
        md = tmp_path / "doc.md"
        md.write_text("Just some plain text.\nNo headers here.\n")
        section = find_doc_section_for_ref(str(md), 2)
        assert section is None

    def test_nonexistent_file_returns_none(self):
        """Missing file returns None."""
        section = find_doc_section_for_ref("/nonexistent.md", 1)
        assert section is None

    def test_finds_top_level_header(self, tmp_path):
        """Falls back to top-level # header if no closer one."""
        md = tmp_path / "doc.md"
        md.write_text(
            "# Main Title\n"
            "\n"
            "Content here.\n"
        )
        section = find_doc_section_for_ref(str(md), 3)
        assert section == "Main Title"
