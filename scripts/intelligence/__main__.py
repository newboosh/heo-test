"""Module entry point for running scripts.intelligence as a package.

Allows: python -m scripts.intelligence <command>
"""

from scripts.intelligence.cli import main
import sys

if __name__ == '__main__':
    sys.exit(main())
