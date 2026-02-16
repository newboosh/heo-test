"""Shared types and utilities for schema validation.

Provides the common building blocks used across skill-specific validators
(problem_definition, requirements_engineering, etc.). Mirrors the patterns
established in scripts/sprint/validate.py and scripts/intelligence/schema.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Constants (shared across validators)
# ---------------------------------------------------------------------------

VALID_CONFIDENCES: list[str] = ["high", "medium", "low"]

VALID_HANDOFF_STATUSES: list[str] = ["complete", "draft", "failed", "blocked"]


# ---------------------------------------------------------------------------
# Error class (mirrors scripts/sprint/validate.py SprintError)
# ---------------------------------------------------------------------------


class SchemaError(Exception):
    """Error in schema validation.

    Attributes:
        message: Human-readable error description.
        file: Path to the file that caused the error.
        line: Line number where the error was detected.
        error_type: Machine-readable error category.
    """

    def __init__(
        self,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        error_type: str = "schema_invalid",
    ):
        super().__init__(message)
        self.message = message
        self.file = file
        self.line = line
        self.error_type = error_type

    def to_json(self) -> dict[str, Any]:
        """Serialize error to JSON format for machine parsing."""
        result: dict[str, Any] = {
            "error": self.error_type,
            "message": self.message,
        }
        if self.file:
            result["file"] = self.file
        if self.line:
            result["line"] = self.line
        return result

    def __str__(self) -> str:
        parts = [self.message]
        if self.file:
            parts.append(f"file: {self.file}")
        if self.line:
            parts.append(f"line: {self.line}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Dataclasses (shared across validators)
# ---------------------------------------------------------------------------


@dataclass
class SignalsBlock:
    """The signals section of a handoff envelope."""

    pass_: bool
    confidence: str
    blockers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 1: YAML parsing (shared utility)
# ---------------------------------------------------------------------------


def load_yaml(yaml_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        Parsed YAML data as a dictionary.

    Raises:
        SchemaError: If file is missing, unreadable, or contains invalid YAML.
    """
    file_str = str(yaml_path)

    if not yaml_path.exists():
        raise SchemaError(
            f"File not found: {yaml_path}",
            file=file_str,
            error_type="file_missing",
        )

    try:
        content = yaml_path.read_text(encoding="utf-8")
    except OSError as e:
        raise SchemaError(
            f"Cannot read file: {e}",
            file=file_str,
            error_type="file_unreadable",
        )

    if not content.strip():
        raise SchemaError("File is empty", file=file_str)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise SchemaError(
            f"Invalid YAML: {e}",
            file=file_str,
            error_type="yaml_parse",
        )

    if not isinstance(data, dict):
        raise SchemaError(
            "YAML must be a mapping (not a list or scalar)",
            file=file_str,
        )

    return data


def parse_signals(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> SignalsBlock:
    """Parse signals block from raw dictionary.

    Args:
        data: Raw YAML data containing a 'signals' key.
        file: Source file path for error reporting.

    Returns:
        Parsed SignalsBlock.

    Raises:
        SchemaError: If signals block is missing or malformed.
    """
    signals = data.get("signals")
    if signals is None:
        raise SchemaError("Missing required 'signals' block", file=file)
    if not isinstance(signals, dict):
        raise SchemaError("'signals' must be a mapping", file=file)

    if "pass" not in signals:
        raise SchemaError(
            "Missing required field 'pass' in signals block",
            file=file,
        )

    raw_pass = signals["pass"]
    if not isinstance(raw_pass, bool):
        raise SchemaError("'signals.pass' must be a boolean", file=file)

    raw_blockers = signals.get("blockers", [])
    if raw_blockers is None:
        raw_blockers = []
    if not isinstance(raw_blockers, list):
        raise SchemaError("'signals.blockers' must be a list", file=file)

    return SignalsBlock(
        pass_=raw_pass,
        confidence=str(signals.get("confidence", "low")),
        blockers=[str(blocker) for blocker in raw_blockers],
    )


# ---------------------------------------------------------------------------
# Shared semantic validators
# ---------------------------------------------------------------------------


def validate_iso_timestamp(timestamp: str, file: Optional[str] = None) -> None:
    """Validate that a string is a valid ISO 8601 timestamp.

    Args:
        timestamp: Timestamp string to validate.
        file: Source file path for error reporting.

    Raises:
        SchemaError: If timestamp is not valid ISO 8601.
    """
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise SchemaError(
            f"Invalid ISO 8601 timestamp: '{timestamp}'",
            file=file,
        )


def validate_confidence(confidence: str, file: Optional[str] = None) -> None:
    """Validate that confidence is a valid enum value.

    Args:
        confidence: Confidence value to validate.
        file: Source file path for error reporting.

    Raises:
        SchemaError: If confidence is not valid.
    """
    if confidence not in VALID_CONFIDENCES:
        raise SchemaError(
            f"Invalid confidence: '{confidence}'."
            f" Must be one of: {', '.join(VALID_CONFIDENCES)}",
            file=file,
        )


def validate_status(status: str, file: Optional[str] = None) -> None:
    """Validate that status is a valid enum value.

    Args:
        status: Status value to validate.
        file: Source file path for error reporting.

    Raises:
        SchemaError: If status is not valid.
    """
    if status not in VALID_HANDOFF_STATUSES:
        raise SchemaError(
            f"Invalid status: '{status}'."
            f" Must be one of: {', '.join(VALID_HANDOFF_STATUSES)}",
            file=file,
        )
