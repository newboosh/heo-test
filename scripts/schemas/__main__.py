"""CLI entry point for schema validation: python -m scripts.schemas.

Currently routes to problem_definition validation. When additional schema
validators are added (e.g., requirements_engineering), this should be
updated to accept a subcommand selecting which schema to validate.
"""

import sys

from scripts.schemas.problem_definition import main

sys.exit(main())
