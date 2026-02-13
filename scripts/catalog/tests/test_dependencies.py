"""Tests for dependency tracking."""

import pytest
from pathlib import Path

from scripts.catalog.dependencies import (
    extract_imports,
    resolve_import,
    build_dependency_graph,
    ModuleDependencies,
)


class TestExtractImports:
    """Tests for import extraction via AST."""

    def test_simple_import(self, tmp_path):
        """Extract simple import statement."""
        py_file = tmp_path / "app.py"
        py_file.write_text("import os")

        imports = extract_imports(py_file)

        assert "os" in imports

    def test_from_import(self, tmp_path):
        """Extract from...import statement."""
        py_file = tmp_path / "app.py"
        py_file.write_text("from os import path")

        imports = extract_imports(py_file)

        assert "os" in imports

    def test_relative_import(self, tmp_path):
        """Extract relative imports."""
        py_file = tmp_path / "services" / "auth.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text("from . import utils\nfrom ..models import User")

        imports = extract_imports(py_file)

        # Relative imports are stored with dot notation
        assert any("utils" in imp or imp == "." for imp in imports)
        assert any("models" in imp or imp == ".." for imp in imports)

    def test_multiple_imports(self, tmp_path):
        """Extract multiple imports from one statement."""
        py_file = tmp_path / "app.py"
        py_file.write_text("import os, sys, json")

        imports = extract_imports(py_file)

        assert "os" in imports
        assert "sys" in imports
        assert "json" in imports

    def test_from_import_multiple(self, tmp_path):
        """Extract multiple names from one from...import."""
        py_file = tmp_path / "app.py"
        py_file.write_text("from os.path import join, exists, dirname")

        imports = extract_imports(py_file)

        assert "os.path" in imports

    def test_nested_module_import(self, tmp_path):
        """Extract dotted module imports."""
        py_file = tmp_path / "app.py"
        py_file.write_text("from app.models.user import User")

        imports = extract_imports(py_file)

        assert "app.models.user" in imports

    def test_syntax_error_returns_empty(self, tmp_path):
        """Files with syntax errors return empty imports."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("import os\ndef broken(:\n    pass")

        imports = extract_imports(py_file)

        assert imports == []


class TestResolveImport:
    """Tests for import resolution to file paths."""

    def test_resolve_internal_module(self, tmp_path):
        """Resolve import to internal file path."""
        # Create module structure
        (tmp_path / "app" / "models").mkdir(parents=True)
        user_file = tmp_path / "app" / "models" / "user.py"
        user_file.write_text("class User: pass")
        (tmp_path / "app" / "models" / "__init__.py").write_text("")
        (tmp_path / "app" / "__init__.py").write_text("")

        result = resolve_import("app.models.user", tmp_path)

        assert result is not None
        assert result == "app/models/user.py"

    def test_resolve_package_init(self, tmp_path):
        """Resolve package import to __init__.py."""
        (tmp_path / "app" / "models").mkdir(parents=True)
        (tmp_path / "app" / "models" / "__init__.py").write_text("# Models")
        (tmp_path / "app" / "__init__.py").write_text("")

        result = resolve_import("app.models", tmp_path)

        assert result is not None
        assert result == "app/models/__init__.py"

    def test_resolve_external_returns_none(self, tmp_path):
        """External packages return None."""
        result = resolve_import("flask", tmp_path)
        assert result is None

        result = resolve_import("numpy.array", tmp_path)
        assert result is None

    def test_resolve_stdlib_returns_none(self, tmp_path):
        """Standard library imports return None."""
        result = resolve_import("os", tmp_path)
        assert result is None

        result = resolve_import("os.path", tmp_path)
        assert result is None


class TestBuildDependencyGraph:
    """Tests for full dependency graph construction."""

    def test_simple_dependency(self, tmp_path):
        """Build graph with simple dependency."""
        # app.py imports utils
        (tmp_path / "app.py").write_text("from utils import helper")
        (tmp_path / "utils.py").write_text("def helper(): pass")

        graph = build_dependency_graph(tmp_path, ["app.py", "utils.py"])

        app_deps = graph.get("app.py")
        assert app_deps is not None
        assert "utils.py" in app_deps.imports

    def test_reverse_dependencies(self, tmp_path):
        """Build reverse dependency graph (imported_by)."""
        # routes.py imports auth.py
        # tests/test_auth.py imports auth.py
        (tmp_path / "routes.py").write_text("from auth import login")
        (tmp_path / "auth.py").write_text("def login(): pass")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_auth.py").write_text("from auth import login")

        graph = build_dependency_graph(
            tmp_path, ["routes.py", "auth.py", "tests/test_auth.py"]
        )

        auth_deps = graph.get("auth.py")
        assert auth_deps is not None
        # Both routes.py and tests/test_auth.py import auth.py
        assert "routes.py" in auth_deps.imported_by
        assert "tests/test_auth.py" in auth_deps.imported_by

    def test_external_packages_tracked(self, tmp_path):
        """External packages should be tracked separately."""
        (tmp_path / "app.py").write_text("import flask\nfrom requests import get")

        graph = build_dependency_graph(tmp_path, ["app.py"])

        app_deps = graph.get("app.py")
        assert app_deps is not None
        assert "flask" in app_deps.external
        assert "requests" in app_deps.external

    def test_circular_imports_handled(self, tmp_path):
        """Circular imports should not cause infinite loops."""
        # a.py imports b.py imports a.py
        (tmp_path / "a.py").write_text("from b import func_b")
        (tmp_path / "b.py").write_text("from a import func_a")

        # Should complete without hanging
        graph = build_dependency_graph(tmp_path, ["a.py", "b.py"])

        a_deps = graph.get("a.py")
        b_deps = graph.get("b.py")

        assert a_deps is not None
        assert b_deps is not None
        assert "b.py" in a_deps.imports
        assert "a.py" in b_deps.imports
        assert "a.py" in b_deps.imported_by  # b imports a
        assert "b.py" in a_deps.imported_by  # a imports b


class TestModuleDependencies:
    """Tests for ModuleDependencies data structure."""

    def test_has_all_fields(self, tmp_path):
        """ModuleDependencies should have all required fields."""
        (tmp_path / "app.py").write_text("import os")

        graph = build_dependency_graph(tmp_path, ["app.py"])
        deps = graph.get("app.py")

        assert deps is not None
        assert hasattr(deps, "imports")
        assert hasattr(deps, "imported_by")
        assert hasattr(deps, "external")

    def test_empty_lists_by_default(self, tmp_path):
        """Files with no imports should have empty lists."""
        (tmp_path / "empty.py").write_text("x = 1")

        graph = build_dependency_graph(tmp_path, ["empty.py"])
        deps = graph.get("empty.py")

        assert deps is not None
        assert deps.imports == []
        assert deps.imported_by == []
        assert deps.external == []
