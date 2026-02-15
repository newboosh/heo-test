"""Librarian - Documentation reference management system.

This package provides tools for:
- Building a symbol index of all code definitions
- Extracting code references from documentation
- Resolving references to exact code locations
- Checking for staleness via content hashing
- Generating fix prompts for the librarian agent

Usage:
    python -m scripts.librarian.doclinks build   # Build doc links
    python -m scripts.librarian.doclinks check   # Check for staleness
    python -m scripts.librarian.doclinks status  # Show status
    python -m scripts.librarian.doclinks fix     # Generate fix prompts
"""

__version__ = "1.0.0"
