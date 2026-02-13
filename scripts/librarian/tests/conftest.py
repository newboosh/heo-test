"""Shared fixtures for librarian tests."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_python_project(tmp_path):
    """Create a minimal Python project with known symbols."""
    # app/models/user.py
    models_dir = tmp_path / "app" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "__init__.py").write_text("")
    (tmp_path / "app" / "__init__.py").write_text("")

    (models_dir / "user.py").write_text(
        '"""User model module."""\n'
        "\n"
        "MAX_NAME_LENGTH = 100\n"
        "\n"
        "\n"
        "class User:\n"
        '    """A user in the system."""\n'
        "\n"
        "    def __init__(self, name: str, email: str):\n"
        "        self.name = name\n"
        "        self.email = email\n"
        "\n"
        "    def display_name(self) -> str:\n"
        '        """Return display name."""\n'
        "        return self.name\n"
    )

    # app/services/auth.py
    services_dir = tmp_path / "app" / "services"
    services_dir.mkdir(parents=True)
    (services_dir / "__init__.py").write_text("")

    (services_dir / "auth.py").write_text(
        '"""Authentication service."""\n'
        "\n"
        "from app.models.user import User\n"
        "\n"
        "\n"
        "def authenticate(username: str, password: str) -> bool:\n"
        '    """Authenticate a user."""\n'
        "    return True\n"
        "\n"
        "\n"
        "async def refresh_token(token: str) -> str:\n"
        '    """Refresh an auth token."""\n'
        '    return "new_token"\n'
    )

    # scripts/utils/helper.py
    utils_dir = tmp_path / "scripts" / "utils"
    utils_dir.mkdir(parents=True)
    (tmp_path / "scripts" / "__init__.py").write_text("")
    (utils_dir / "__init__.py").write_text("")

    (utils_dir / "helper.py").write_text(
        '"""Utility helpers."""\n'
        "\n"
        "DEFAULT_TIMEOUT = 30\n"
        "\n"
        "\n"
        "def format_name(first: str, last: str) -> str:\n"
        '    """Format a full name."""\n'
        '    return f"{first} {last}"\n'
    )

    return tmp_path


@pytest.fixture
def sample_markdown_docs(sample_python_project):
    """Create markdown docs that reference the Python symbols."""
    root = sample_python_project
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)

    (docs_dir / "api.md").write_text(
        "# API Reference\n"
        "\n"
        "## Authentication\n"
        "\n"
        "The `authenticate` function handles user login.\n"
        "See `app/services/auth.py` for implementation.\n"
        "\n"
        "## Models\n"
        "\n"
        "The `User` class represents a user entity.\n"
        "Stored in `app/models/user.py`.\n"
        "\n"
        "```python\n"
        "from app.services.auth import authenticate\n"
        "```\n"
    )

    (docs_dir / "architecture.md").write_text(
        "# Architecture\n"
        "\n"
        "## Helpers\n"
        "\n"
        "The `format_name` utility is used for display.\n"
        "See `scripts/utils/helper.py`.\n"
    )

    # Create indexes dir (should be skipped)
    indexes_dir = docs_dir / "indexes"
    indexes_dir.mkdir(exist_ok=True)
    (indexes_dir / "old_index.md").write_text("# should be skipped\n")

    return root


@pytest.fixture
def sample_symbol_index(sample_python_project):
    """Build and return a SymbolIndex from the sample project."""
    from scripts.librarian.symbol_indexer import build_symbol_index

    return build_symbol_index(
        root=sample_python_project,
        index_dirs=["app", "scripts"],
    )


@pytest.fixture
def sample_known_symbols(sample_symbol_index):
    """Get known symbols set from sample index."""
    from scripts.librarian.symbol_indexer import get_known_symbols

    return get_known_symbols(sample_symbol_index)
