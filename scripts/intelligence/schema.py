"""Schema versioning and migration for intelligence system.

Manages JSON schema versions and provides migration functions
to handle format changes over time.
"""

from typing import Any, Dict, Optional
import json

CURRENT_VERSION = "1.0.0"


class Schema:
    """Manage schema versions and migrations."""

    @staticmethod
    def current_version() -> str:
        """Get current schema version.

        Returns:
            Version string (e.g., "1.0.0").
        """
        return CURRENT_VERSION

    @staticmethod
    def add_version(data: Dict[str, Any]) -> Dict[str, Any]:
        """Add version field to data structure.

        Args:
            data: Data dictionary.

        Returns:
            Data with version field added.
        """
        return {
            **data,
            "_schema_version": CURRENT_VERSION
        }

    @staticmethod
    def get_version(data: Dict[str, Any]) -> str:
        """Get schema version from data.

        Args:
            data: Data dictionary.

        Returns:
            Version string or "0.0.0" if not found.
        """
        return data.get("_schema_version", "0.0.0")

    @staticmethod
    def load_index(file_path: str) -> Optional[Dict[str, Any]]:
        """Load index with automatic migration.

        Loads JSON file and applies any necessary migrations
        to upgrade format to current version.

        Args:
            file_path: Path to index JSON file.

        Returns:
            Loaded and migrated data, or None if load fails.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        # Get data version and apply migrations if needed
        data_version = Schema.get_version(data)
        current = CURRENT_VERSION

        if data_version != current:
            data = Schema.migrate(data, data_version, current)

        return data

    @staticmethod
    def dump_index(data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for JSON output with current version.

        Args:
            data: Data to output.

        Returns:
            Data with version field set to current version.
        """
        return Schema.add_version(data)

    @staticmethod
    def migrate(data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """Migrate data from one version to another.

        Args:
            data: Data to migrate.
            from_version: Starting version.
            to_version: Target version.

        Returns:
            Migrated data.
        """
        # Parse versions into (major, minor, patch)
        def parse_version(v: str) -> tuple:
            parts = v.split('.')
            return tuple(int(p) for p in parts)

        from_v = parse_version(from_version)
        to_v = parse_version(to_version)

        # Apply migrations in order
        current = data.copy()

        # Migrations from v0.0.0 to v1.0.0
        if from_v < (1, 0, 0) <= to_v:
            current = Schema._migrate_v0_to_v1(current)

        # Add more migration paths as needed in future versions

        return current

    @staticmethod
    def _migrate_v0_to_v1(data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v0.0.0 to v1.0.0.

        This migration:
        - Adds schema version field
        - Ensures standard structure

        Args:
            data: Data in v0 format.

        Returns:
            Data in v1 format.
        """
        # Ensure standard fields exist
        migrated = {
            **data,
            "_schema_version": "1.0.0"
        }

        # Ensure index arrays exist
        for key in ["symbols", "files", "dependencies"]:
            if key not in migrated:
                migrated[key] = []

        # Ensure metadata exists
        if "metadata" not in migrated:
            migrated["metadata"] = {
                "generated_at": None,
                "root_dir": None,
                "total_files": 0,
                "total_symbols": 0
            }

        return migrated
