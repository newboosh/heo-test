"""Tests for AST utilities (symbol extraction and hashing)."""

import pytest
from pathlib import Path

from scripts.librarian.utils.ast_utils import (
    extract_symbols_from_file,
    hash_file,
    hash_symbol,
    get_symbol_source,
)


class TestExtractSymbolsFromFile:
    """Tests for extract_symbols_from_file."""

    def test_extract_functions(self, tmp_path):
        """Extract top-level function definitions."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "def greet(name: str) -> str:\n"
            '    return f"Hello {name}"\n'
            "\n"
            "def farewell():\n"
            "    pass\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        names = [s["name"] for s in symbols]
        assert "greet" in names
        assert "farewell" in names
        func = next(s for s in symbols if s["name"] == "greet")
        assert func["type"] == "function"
        assert func["line"] == 1
        assert "name: str" in func["signature"]

    def test_extract_classes(self, tmp_path):
        """Extract class definitions."""
        py_file = tmp_path / "models.py"
        py_file.write_text(
            "class Animal:\n"
            "    pass\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        cls = next(s for s in symbols if s["name"] == "Animal")
        assert cls["type"] == "class"
        assert cls["signature"] == "class Animal"

    def test_extract_class_methods(self, tmp_path):
        """Extract methods using ClassName.method_name format."""
        py_file = tmp_path / "service.py"
        py_file.write_text(
            "class Service:\n"
            "    def start(self):\n"
            "        pass\n"
            "\n"
            "    def stop(self):\n"
            "        pass\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        names = [s["name"] for s in symbols]
        assert "Service.start" in names
        assert "Service.stop" in names
        method = next(s for s in symbols if s["name"] == "Service.start")
        assert method["type"] == "method"

    def test_extract_async_functions(self, tmp_path):
        """Async functions are extracted as type function."""
        py_file = tmp_path / "async_mod.py"
        py_file.write_text(
            "async def fetch_data(url: str) -> dict:\n"
            "    pass\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        func = symbols[0]
        assert func["name"] == "fetch_data"
        assert func["type"] == "function"

    def test_extract_constants(self, tmp_path):
        """UPPER_CASE assignments are extracted as constants."""
        py_file = tmp_path / "config.py"
        py_file.write_text(
            "MAX_SIZE = 1024\n"
            "DEFAULT_NAME = 'test'\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        names = [s["name"] for s in symbols]
        assert "MAX_SIZE" in names
        assert "DEFAULT_NAME" in names
        const = next(s for s in symbols if s["name"] == "MAX_SIZE")
        assert const["type"] == "constant"

    def test_lowercase_assignments_ignored(self, tmp_path):
        """Lowercase variable assignments are not extracted."""
        py_file = tmp_path / "vars.py"
        py_file.write_text(
            "my_var = 42\n"
            "another_thing = 'hello'\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        assert len(symbols) == 0

    def test_nonexistent_file_returns_empty(self):
        """Missing file returns empty list."""
        symbols = extract_symbols_from_file("/nonexistent/path.py")
        assert symbols == []

    def test_syntax_error_returns_empty(self, tmp_path):
        """File with syntax error returns empty list."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass\n")
        symbols = extract_symbols_from_file(str(py_file))
        assert symbols == []

    def test_function_signature_with_annotations(self, tmp_path):
        """Type annotations appear in signature."""
        py_file = tmp_path / "typed.py"
        py_file.write_text(
            "def process(x: int, y: str = 'default') -> bool:\n"
            "    return True\n"
        )
        symbols = extract_symbols_from_file(str(py_file))
        sig = symbols[0]["signature"]
        assert "x: int" in sig
        assert "-> bool" in sig


class TestHashFile:
    """Tests for hash_file."""

    def test_hash_produces_sha256(self, tmp_path):
        """Hash is a 64-character hex string (SHA-256)."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        h = hash_file(str(f))
        assert h is not None
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_changes_with_content(self, tmp_path):
        """Different content produces different hash."""
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert hash_file(str(f1)) != hash_file(str(f2))

    def test_hash_same_for_same_content(self, tmp_path):
        """Same content in different files produces same hash."""
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("identical")
        f2.write_text("identical")
        assert hash_file(str(f1)) == hash_file(str(f2))

    def test_hash_nonexistent_returns_none(self):
        """Missing file returns None."""
        assert hash_file("/nonexistent/file.py") is None


class TestHashSymbol:
    """Tests for hash_symbol."""

    def test_hash_function(self, tmp_path):
        """Hash a top-level function."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "def greet(name):\n"
            "    return name\n"
        )
        h = hash_symbol(str(py_file), "greet")
        assert h is not None
        assert len(h) == 64

    def test_hash_class(self, tmp_path):
        """Hash a class definition."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "class Foo:\n"
            "    x = 1\n"
        )
        h = hash_symbol(str(py_file), "Foo")
        assert h is not None

    def test_hash_method(self, tmp_path):
        """Hash a method using dotted Class.method format."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "class MyClass:\n"
            "    def my_method(self):\n"
            "        pass\n"
        )
        h = hash_symbol(str(py_file), "MyClass.my_method")
        assert h is not None

    def test_hash_nonexistent_symbol_returns_none(self, tmp_path):
        """Symbol not in file returns None."""
        py_file = tmp_path / "mod.py"
        py_file.write_text("x = 1\n")
        assert hash_symbol(str(py_file), "nonexistent") is None

    def test_hash_nonexistent_file_returns_none(self):
        """Missing file returns None."""
        assert hash_symbol("/nonexistent.py", "func") is None

    def test_hash_syntax_error_returns_none(self, tmp_path):
        """File with syntax error returns None."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass\n")
        assert hash_symbol(str(py_file), "broken") is None

    def test_hash_ignores_formatting(self, tmp_path):
        """Same function with different whitespace produces same AST hash."""
        f1 = tmp_path / "v1.py"
        f1.write_text(
            "def calc(x):\n"
            "    return x + 1\n"
        )
        f2 = tmp_path / "v2.py"
        f2.write_text(
            "def calc(x):\n"
            "    # a comment\n"
            "    return x + 1\n"
        )
        h1 = hash_symbol(str(f1), "calc")
        h2 = hash_symbol(str(f2), "calc")
        # Comments are stripped during parsing and don't appear in the AST
        assert h1 == h2


class TestGetSymbolSource:
    """Tests for get_symbol_source."""

    def test_get_function_source(self, tmp_path):
        """Return exact source lines of a function."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "def greet(name):\n"
            '    return f"Hello {name}"\n'
        )
        source = get_symbol_source(str(py_file), "greet")
        assert source is not None
        assert "def greet" in source
        assert "Hello" in source

    def test_get_class_source(self, tmp_path):
        """Return full class body."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "class Animal:\n"
            "    species = 'unknown'\n"
            "\n"
            "    def speak(self):\n"
            "        pass\n"
        )
        source = get_symbol_source(str(py_file), "Animal")
        assert source is not None
        assert "class Animal" in source
        assert "speak" in source

    def test_get_method_source(self, tmp_path):
        """Return method source via dotted name."""
        py_file = tmp_path / "mod.py"
        py_file.write_text(
            "class Service:\n"
            "    def run(self):\n"
            "        return True\n"
        )
        source = get_symbol_source(str(py_file), "Service.run")
        assert source is not None
        assert "def run" in source

    def test_nonexistent_symbol_returns_none(self, tmp_path):
        """Symbol not in file returns None."""
        py_file = tmp_path / "mod.py"
        py_file.write_text("x = 1\n")
        assert get_symbol_source(str(py_file), "missing") is None

    def test_syntax_error_returns_none(self, tmp_path):
        """File with syntax error returns None."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass\n")
        assert get_symbol_source(str(py_file), "broken") is None

    def test_nonexistent_file_returns_none(self):
        """Missing file returns None."""
        assert get_symbol_source("/nonexistent.py", "func") is None
