"""Unified code intelligence system.

This package provides a unified interface for code analysis, combining:
- File classification (catalog layer)
- Dependency tracking (catalog layer)
- Symbol indexing (librarian layer)
- Docstring parsing (librarian layer)

The system uses DAG-based orchestration with incremental caching for
efficient incremental builds.
"""

__version__ = "0.1.0"
__author__ = "Claude Code"
