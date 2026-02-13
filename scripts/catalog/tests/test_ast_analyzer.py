"""Tests for AST analysis of Python files."""

import pytest
from pathlib import Path
import tempfile

from scripts.catalog.ast_analyzer import (
    check_class_inherits,
    check_decorator,
    check_has_main_block,
    match_ast_condition,
)


class TestClassInherits:
    """Tests for class_inherits:NAME detection."""

    def test_simple_inheritance(self, tmp_path):
        """Match simple single inheritance."""
        py_file = tmp_path / "model.py"
        py_file.write_text("""
class User(BaseModel):
    pass
""")
        assert check_class_inherits(py_file, "BaseModel")
        assert not check_class_inherits(py_file, "OtherModel")

    def test_multiple_inheritance(self, tmp_path):
        """Match when name appears in multiple inheritance."""
        py_file = tmp_path / "model.py"
        py_file.write_text("""
class User(Mixin, BaseModel, Serializable):
    pass
""")
        assert check_class_inherits(py_file, "BaseModel")
        assert check_class_inherits(py_file, "Mixin")
        assert check_class_inherits(py_file, "Serializable")
        assert not check_class_inherits(py_file, "OtherModel")

    def test_qualified_name_no_match(self, tmp_path):
        """Should not match when qualified differently."""
        py_file = tmp_path / "model.py"
        py_file.write_text("""
class User(pydantic.BaseModel):
    pass
""")
        # BaseModel without qualifier should NOT match pydantic.BaseModel
        assert not check_class_inherits(py_file, "BaseModel")
        # Full qualified name should match
        assert check_class_inherits(py_file, "pydantic.BaseModel")

    def test_indirect_inheritance_no_match(self, tmp_path):
        """Should not match indirect inheritance (only direct parents)."""
        py_file = tmp_path / "widget.py"
        py_file.write_text("""
# StatelessWidget extends Widget in another file
class MyWidget(StatelessWidget):
    pass
""")
        # MyWidget extends StatelessWidget, not Widget directly
        assert not check_class_inherits(py_file, "Widget")
        assert check_class_inherits(py_file, "StatelessWidget")

    def test_multiple_classes_in_file(self, tmp_path):
        """Should match if ANY class in file inherits."""
        py_file = tmp_path / "models.py"
        py_file.write_text("""
class Helper:
    pass

class User(BaseModel):
    pass

class Admin(User):
    pass
""")
        assert check_class_inherits(py_file, "BaseModel")
        assert check_class_inherits(py_file, "User")
        assert not check_class_inherits(py_file, "Helper")  # No class inherits Helper


class TestDecorator:
    """Tests for decorator:NAME detection."""

    def test_simple_decorator(self, tmp_path):
        """Match simple decorator without arguments."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@app.route
def handler():
    pass
""")
        assert check_decorator(py_file, "app.route")

    def test_decorator_with_args(self, tmp_path):
        """Match decorator with arguments."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@app.route("/users")
def get_users():
    pass
""")
        assert check_decorator(py_file, "app.route")

    def test_multiple_decorators(self, tmp_path):
        """Match among multiple decorators."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@app.route("/admin")
@login_required
@cache(timeout=300)
def admin_panel():
    pass
""")
        assert check_decorator(py_file, "app.route")
        assert check_decorator(py_file, "login_required")
        assert check_decorator(py_file, "cache")

    def test_decorator_on_class(self, tmp_path):
        """Match decorator on class definition."""
        py_file = tmp_path / "config.py"
        py_file.write_text("""
@dataclass
class Config:
    name: str
""")
        assert check_decorator(py_file, "dataclass")

    def test_qualified_decorator_no_match(self, tmp_path):
        """Should not match different qualifier."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@blueprint.route("/users")
def get_users():
    pass
""")
        assert not check_decorator(py_file, "app.route")
        assert check_decorator(py_file, "blueprint.route")

    def test_fully_qualified_decorator(self, tmp_path):
        """Match fully qualified decorator name."""
        py_file = tmp_path / "compute.py"
        py_file.write_text("""
@functools.lru_cache(maxsize=128)
def expensive_computation():
    pass
""")
        assert check_decorator(py_file, "functools.lru_cache")

    def test_callable_forms_equivalent(self, tmp_path):
        """@foo and @foo() both match decorator:foo."""
        py_file1 = tmp_path / "test1.py"
        py_file1.write_text("""
@pytest.mark.skip
def test_one():
    pass
""")
        py_file2 = tmp_path / "test2.py"
        py_file2.write_text("""
@pytest.mark.skip()
def test_two():
    pass
""")
        assert check_decorator(py_file1, "pytest.mark.skip")
        assert check_decorator(py_file2, "pytest.mark.skip")


class TestHasMainBlock:
    """Tests for has_main_block detection."""

    def test_standard_main_block(self, tmp_path):
        """Match standard if __name__ == '__main__' pattern."""
        py_file = tmp_path / "main.py"
        py_file.write_text('''
def main():
    print("Hello")

if __name__ == "__main__":
    main()
''')
        assert check_has_main_block(py_file)

    def test_single_quotes(self, tmp_path):
        """Match with single quotes."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
if __name__ == '__main__':
    run()
""")
        assert check_has_main_block(py_file)

    def test_extra_spaces(self, tmp_path):
        """Match with extra whitespace."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
if __name__  ==  "__main__":
    start()
""")
        assert check_has_main_block(py_file)

    def test_reversed_comparison_no_match(self, tmp_path):
        """Should not match reversed comparison (non-idiomatic)."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
if "__main__" == __name__:
    main()
""")
        assert not check_has_main_block(py_file)

    def test_nested_no_match(self, tmp_path):
        """Should not match if nested inside function."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
def setup():
    if __name__ == "__main__":
        pass
""")
        assert not check_has_main_block(py_file)

    def test_different_variable_no_match(self, tmp_path):
        """Should not match with different variable name."""
        py_file = tmp_path / "main.py"
        py_file.write_text("""
if module_name == "__main__":
    main()
""")
        assert not check_has_main_block(py_file)

    def test_no_main_block(self, tmp_path):
        """Should not match files without main block."""
        py_file = tmp_path / "utils.py"
        py_file.write_text("""
def helper():
    pass
""")
        assert not check_has_main_block(py_file)


class TestMatchAstCondition:
    """Tests for the unified match_ast_condition interface."""

    def test_class_inherits_condition(self, tmp_path):
        """Parse and match class_inherits condition."""
        py_file = tmp_path / "model.py"
        py_file.write_text("""
class User(BaseModel):
    pass
""")
        assert match_ast_condition(py_file, "class_inherits:BaseModel")
        assert not match_ast_condition(py_file, "class_inherits:OtherModel")

    def test_decorator_condition(self, tmp_path):
        """Parse and match decorator condition."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
@app.route("/")
def index():
    pass
""")
        assert match_ast_condition(py_file, "decorator:app.route")
        assert not match_ast_condition(py_file, "decorator:blueprint.route")

    def test_has_main_block_condition(self, tmp_path):
        """Parse and match has_main_block condition."""
        py_file = tmp_path / "script.py"
        py_file.write_text('''
if __name__ == "__main__":
    print("running")
''')
        assert match_ast_condition(py_file, "has_main_block")

    def test_invalid_condition_returns_false(self, tmp_path):
        """Invalid condition format should return False gracefully."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1")
        assert not match_ast_condition(py_file, "invalid_condition")
        assert not match_ast_condition(py_file, "")

    def test_non_python_file_returns_false(self, tmp_path):
        """Non-Python files should return False."""
        js_file = tmp_path / "test.js"
        js_file.write_text("class User extends BaseModel {}")
        assert not match_ast_condition(js_file, "class_inherits:BaseModel")

    def test_syntax_error_returns_false(self, tmp_path):
        """Files with syntax errors should return False gracefully."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass")
        assert not match_ast_condition(py_file, "class_inherits:BaseModel")


class TestAliasAndImportLimitations:
    """Tests demonstrating that AST matching is syntactic only."""

    def test_aliased_import_no_match_original(self, tmp_path):
        """Aliased imports should match alias, not original name."""
        py_file = tmp_path / "model.py"
        py_file.write_text("""
from pydantic import BaseModel as BM

class User(BM):
    pass
""")
        # Should NOT match original name
        assert not check_class_inherits(py_file, "BaseModel")
        # Should match the alias
        assert check_class_inherits(py_file, "BM")

    def test_variable_assignment_no_resolve(self, tmp_path):
        """Variable assignments are not resolved."""
        py_file = tmp_path / "routes.py"
        py_file.write_text("""
import flask
app = flask.Flask(__name__)
my_app = app

@my_app.route("/")
def index():
    pass
""")
        # Matches syntactic name
        assert check_decorator(py_file, "my_app.route")
        # Does NOT match through variable assignment
        assert not check_decorator(py_file, "app.route")
