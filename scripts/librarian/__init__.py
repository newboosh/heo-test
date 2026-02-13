"""Librarian - Documentation reference management system.

This package provides tools for:
- Building a symbol index of all code definitions
- Extracting code references from documentation
- Resolving references to exact code locations
- Checking for staleness via content hashing
- Generating fix prompts for the librarian agent

Usage:
    python -m scripts.librarian.catalog build   # Build full catalog
    python -m scripts.librarian.catalog check   # Check for staleness
    python -m scripts.librarian.catalog status  # Show status
    python -m scripts.librarian.catalog fix     # Generate fix prompts
"""

__version__ = "1.0.0"
