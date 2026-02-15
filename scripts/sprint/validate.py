"""Sprint YAML schema validation and state management.

Validates .sprint/*.yaml handoff files against the handoff protocol
defined in docs/SPRINT_LIFECYCLE.md. Follows the catalog config.py
validation pattern (three-stage: parse → structure → semantics) and
the intelligence schema.py versioning pattern (_schema_version field).

Usage:
    python -m scripts.sprint.validate [sprint_dir]

Examples:
    python -m scripts.sprint.validate .sprint/
    python -m scripts.sprint.validate
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


# ---------------------------------------------------------------------------
# Schema version (mirrors scripts/intelligence/schema.py pattern)
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHASE_NAMES: list[str] = [
    "intake",
    "refinement",
    "design",
    "technical_planning",
    "backlog",
    "implementation",
    "code_review",
    "qa",
    "security_review",
    "ci_cd",
    "merge",
    "monitoring",
    "retrospective",
]

PHASE_NAME_MAP: dict[int, str] = dict(enumerate(PHASE_NAMES, start=1))

DEPENDS_ON_MAP: dict[int, Optional[str]] = {
    1: None,
    2: "intake",
    3: "refinement",
    4: "design",
    5: "technical_planning",
    6: "backlog",
    7: "implementation",
    8: "code_review",
    9: "qa",
    10: "security_review",
    11: "ci_cd",
    12: "merge",
    13: "monitoring",
}

PHASE_OUTPUT_FILES: dict[int, str] = {
    1: "input.yaml",
    2: "product.yaml",
    3: "design.yaml",
    4: "technical.yaml",
    5: "backlog.yaml",
    6: "execution-status.yaml",
    7: "review-code.yaml",
    8: "qa-report.yaml",
    9: "review-security.yaml",
    10: "ci-report.yaml",
    11: "merge-report.yaml",
    12: "monitoring-report.yaml",
    13: "retrospective.yaml",
}

VALID_PHASES: list[int] = list(range(1, 14))

VALID_STATUSES: list[str] = ["complete", "failed", "blocked"]

VALID_CONFIDENCES: list[str] = ["high", "medium", "low"]

VALID_ROLES: list[str] = [
    "developer",
    "product_manager",
    "ux_designer",
    "api_designer",
    "tech_lead",
    "developer_agent",
    "senior_developer",
    "security_engineer",
    "qa_engineer",
    "devops",
    "devops_engineer",
    "release_manager",
    "sre",
    "scrum_master",
]

VALID_VELOCITY_MODES: list[str] = ["autonomous", "attended"]

VALID_META_STATUSES: list[str] = [
    "in_progress",
    "complete",
    "blocked",
    "failed",
]


# ---------------------------------------------------------------------------
# Error class (mirrors scripts/catalog/config.py ConfigError)
# ---------------------------------------------------------------------------


class SprintError(Exception):
    """Error in sprint YAML validation.

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
        error_type: str = "sprint_invalid",
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
# Dataclasses (catalog pattern)
# ---------------------------------------------------------------------------


@dataclass
class SignalsBlock:
    """The signals section of a handoff envelope."""

    pass_: bool
    confidence: str
    blockers: list[str] = field(default_factory=list)


@dataclass
class HandoffEnvelope:
    """Standard handoff fields present in every sprint phase output."""

    phase: int
    phase_name: str
    role: str
    status: str
    timestamp: str
    depends_on: Optional[str]
    summary: str
    outputs: list[str]
    open_issues: list[str]
    signals: SignalsBlock


@dataclass
class PhaseLogEntry:
    """A single entry in the sprint phase completion log."""

    phase: int
    phase_name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    output_file: str
    validated: bool = False


@dataclass
class SprintMeta:
    """Sprint metadata and state tracking."""

    sprint_id: str
    schema_version: str
    started: str
    velocity_mode: str
    requirements: str
    current_phase: int
    status: str
    phase_log: list[PhaseLogEntry] = field(default_factory=list)
    phases_failed: list[int] = field(default_factory=list)
    retry_count: int = 0
    revision_cycles: int = 0
    last_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Stage 1: YAML parsing
# ---------------------------------------------------------------------------


def _load_yaml(yaml_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        Parsed YAML data as a dictionary.

    Raises:
        SprintError: If file is missing, unreadable, or contains invalid YAML.
    """
    file_str = str(yaml_path)

    if not yaml_path.exists():
        raise SprintError(
            f"File not found: {yaml_path}",
            file=file_str,
            error_type="file_missing",
        )

    try:
        content = yaml_path.read_text(encoding="utf-8")
    except OSError as e:
        raise SprintError(
            f"Cannot read file: {e}",
            file=file_str,
            error_type="file_unreadable",
        )

    if not content.strip():
        raise SprintError("File is empty", file=file_str)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise SprintError(
            f"Invalid YAML: {e}",
            file=file_str,
            error_type="yaml_parse",
        )

    if not isinstance(data, dict):
        raise SprintError(
            "Sprint YAML must be a mapping",
            file=file_str,
        )

    return data


# ---------------------------------------------------------------------------
# Stage 2: Structure mapping
# ---------------------------------------------------------------------------


def _parse_signals(
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
        SprintError: If signals block is missing or malformed.
    """
    signals = data.get("signals")
    if signals is None:
        raise SprintError("Missing required 'signals' block", file=file)
    if not isinstance(signals, dict):
        raise SprintError("'signals' must be a mapping", file=file)

    if "pass" not in signals:
        raise SprintError(
            "Missing required field 'pass' in signals block",
            file=file,
        )

    return SignalsBlock(
        pass_=bool(signals["pass"]),
        confidence=str(signals.get("confidence", "low")),
        blockers=list(signals.get("blockers", [])),
    )


def _parse_envelope(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> HandoffEnvelope:
    """Map raw YAML dictionary to HandoffEnvelope dataclass.

    Args:
        data: Raw YAML data.
        file: Source file path for error reporting.

    Returns:
        Parsed HandoffEnvelope.

    Raises:
        SprintError: If required fields are missing.
    """
    required_fields = [
        "phase",
        "phase_name",
        "role",
        "status",
        "timestamp",
        "summary",
    ]
    for key in required_fields:
        if key not in data:
            raise SprintError(
                f"Missing required field: '{key}'",
                file=file,
            )

    return HandoffEnvelope(
        phase=data["phase"],
        phase_name=data["phase_name"],
        role=data["role"],
        status=data["status"],
        timestamp=str(data["timestamp"]),
        depends_on=data.get("depends_on"),
        summary=str(data["summary"]),
        outputs=list(data.get("outputs", [])),
        open_issues=list(data.get("open_issues", [])),
        signals=_parse_signals(data, file),
    )


# ---------------------------------------------------------------------------
# Stage 3: Semantic validation
# ---------------------------------------------------------------------------


def _validate_iso_timestamp(timestamp: str, file: Optional[str] = None) -> None:
    """Validate that a string is a valid ISO 8601 timestamp.

    Args:
        timestamp: Timestamp string to validate.
        file: Source file path for error reporting.

    Raises:
        SprintError: If timestamp is not valid ISO 8601.
    """
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise SprintError(
            f"Invalid ISO 8601 timestamp: '{timestamp}'",
            file=file,
        )


def validate_envelope(
    envelope: HandoffEnvelope,
    file: Optional[str] = None,
) -> None:
    """Validate semantic correctness of a handoff envelope.

    Checks phase/name consistency, depends_on chain, timestamp format,
    and enum membership.

    Args:
        envelope: Parsed handoff envelope.
        file: Source file path for error reporting.

    Raises:
        SprintError: If any semantic validation fails.
    """
    if envelope.phase not in VALID_PHASES:
        raise SprintError(
            f"Invalid phase: {envelope.phase}. Must be 1-13.",
            file=file,
        )

    expected_name = PHASE_NAME_MAP.get(envelope.phase)
    if envelope.phase_name != expected_name:
        raise SprintError(
            f"phase_name '{envelope.phase_name}' doesn't match phase"
            f" {envelope.phase}. Expected '{expected_name}'.",
            file=file,
        )

    if envelope.role not in VALID_ROLES:
        raise SprintError(
            f"Invalid role: '{envelope.role}'. Must be one of:"
            f" {', '.join(VALID_ROLES)}",
            file=file,
        )

    if envelope.status not in VALID_STATUSES:
        raise SprintError(
            f"Invalid status: '{envelope.status}'. Must be one of:"
            f" {', '.join(VALID_STATUSES)}",
            file=file,
        )

    if envelope.signals.confidence not in VALID_CONFIDENCES:
        raise SprintError(
            f"Invalid confidence: '{envelope.signals.confidence}'."
            f" Must be one of: {', '.join(VALID_CONFIDENCES)}",
            file=file,
        )

    expected_dep = DEPENDS_ON_MAP.get(envelope.phase)
    if envelope.depends_on != expected_dep:
        raise SprintError(
            f"depends_on should be '{expected_dep}' for phase"
            f" {envelope.phase}, got '{envelope.depends_on}'",
            file=file,
        )

    _validate_iso_timestamp(envelope.timestamp, file)

    # Failed/blocked phases must have blockers or open_issues
    if envelope.status in ("failed", "blocked"):
        has_blockers = bool(envelope.signals.blockers)
        has_issues = bool(envelope.open_issues)
        if not has_blockers and not has_issues:
            raise SprintError(
                f"Phase with status '{envelope.status}' must have"
                " non-empty signals.blockers or open_issues",
                file=file,
            )


# ---------------------------------------------------------------------------
# Phase-specific body validators
# ---------------------------------------------------------------------------


def validate_phase_1_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate intake-specific body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing.
    """
    if "what" not in data:
        raise SprintError(
            "Phase 1 (intake) requires 'what' field",
            file=file,
        )


def validate_phase_2_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate refinement-specific body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "epic" not in data:
        raise SprintError(
            "Phase 2 (refinement) requires 'epic' field",
            file=file,
        )
    if "user_stories" not in data:
        raise SprintError(
            "Phase 2 (refinement) requires 'user_stories' field",
            file=file,
        )
    stories = data["user_stories"]
    if not isinstance(stories, list) or len(stories) == 0:
        raise SprintError(
            "'user_stories' must be a non-empty list",
            file=file,
        )


def validate_phase_3_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate design-specific body fields.

    Supports two design modes:
      - frontend (default): requires 'ux_requirements'
      - backend: requires 'api_contract'

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing.
    """
    valid_design_modes = ["frontend", "backend"]
    design_mode = data.get("design_mode", "frontend")
    if design_mode not in valid_design_modes:
        raise SprintError(
            f"Invalid design_mode: '{design_mode}'."
            f" Must be one of: {', '.join(valid_design_modes)}",
            file=file,
        )
    if design_mode == "backend":
        if "api_contract" not in data:
            raise SprintError(
                "Phase 3 (design, backend mode) requires 'api_contract' field",
                file=file,
            )
    else:
        if "ux_requirements" not in data:
            raise SprintError(
                "Phase 3 (design) requires 'ux_requirements' field",
                file=file,
            )


def validate_phase_4_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate technical planning-specific body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing.
    """
    if "architecture" not in data:
        raise SprintError(
            "Phase 4 (technical_planning) requires 'architecture' field",
            file=file,
        )
    if "changes" not in data:
        raise SprintError(
            "Phase 4 (technical_planning) requires 'changes' field",
            file=file,
        )


def validate_phase_5_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate backlog-specific body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "sprint_backlog" not in data:
        raise SprintError(
            "Phase 5 (backlog) requires 'sprint_backlog' field",
            file=file,
        )
    tasks = data["sprint_backlog"]
    if not isinstance(tasks, list) or len(tasks) == 0:
        raise SprintError(
            "'sprint_backlog' must be a non-empty list",
            file=file,
        )
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise SprintError(
                f"sprint_backlog[{i}] must be a mapping",
                file=file,
            )
        if "id" not in task:
            raise SprintError(
                f"sprint_backlog[{i}] missing 'id' field",
                file=file,
            )
        if "title" not in task:
            raise SprintError(
                f"sprint_backlog[{i}] missing 'title' field",
                file=file,
            )


def validate_phase_6_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate implementation status body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "tasks_completed" not in data:
        raise SprintError(
            "Phase 6 (implementation) requires 'tasks_completed' field",
            file=file,
        )
    if not isinstance(data["tasks_completed"], list):
        raise SprintError(
            "'tasks_completed' must be a list",
            file=file,
        )
    if "execution_stats" not in data:
        raise SprintError(
            "Phase 6 (implementation) requires 'execution_stats' field",
            file=file,
        )
    if not isinstance(data["execution_stats"], dict):
        raise SprintError(
            "'execution_stats' must be a mapping",
            file=file,
        )


def validate_phase_7_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate code review body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "findings" not in data:
        raise SprintError(
            "Phase 7 (code_review) requires 'findings' field",
            file=file,
        )
    findings = data["findings"]
    if not isinstance(findings, list):
        raise SprintError(
            "'findings' must be a list",
            file=file,
        )


def validate_phase_8_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate QA report body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "test_results" not in data:
        raise SprintError(
            "Phase 8 (qa) requires 'test_results' field",
            file=file,
        )
    if not isinstance(data["test_results"], dict):
        raise SprintError(
            "'test_results' must be a mapping",
            file=file,
        )


def validate_phase_9_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate security review body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "findings" not in data:
        raise SprintError(
            "Phase 9 (security_review) requires 'findings' field",
            file=file,
        )
    findings = data["findings"]
    if not isinstance(findings, list):
        raise SprintError(
            "'findings' must be a list",
            file=file,
        )


def validate_phase_10_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate CI/CD report body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "pipeline" not in data:
        raise SprintError(
            "Phase 10 (ci_cd) requires 'pipeline' field",
            file=file,
        )
    if not isinstance(data["pipeline"], dict):
        raise SprintError(
            "'pipeline' must be a mapping",
            file=file,
        )


def validate_phase_11_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate merge report body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "gate_decision" not in data:
        raise SprintError(
            "Phase 11 (merge) requires 'gate_decision' field",
            file=file,
        )
    gate = data["gate_decision"]
    if not isinstance(gate, dict):
        raise SprintError(
            "'gate_decision' must be a mapping",
            file=file,
        )
    if "verdict" not in gate:
        raise SprintError(
            "'gate_decision' requires 'verdict' field",
            file=file,
        )
    valid_verdicts = ["SHIP", "REVISE", "BLOCKED"]
    if gate["verdict"] not in valid_verdicts:
        raise SprintError(
            f"Invalid gate verdict: '{gate['verdict']}'."
            f" Must be one of: {', '.join(valid_verdicts)}",
            file=file,
        )


def validate_phase_12_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate monitoring report body fields.

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    if "health_assessment" not in data:
        raise SprintError(
            "Phase 12 (monitoring) requires 'health_assessment' field",
            file=file,
        )
    health = data["health_assessment"]
    if not isinstance(health, dict):
        raise SprintError(
            "'health_assessment' must be a mapping",
            file=file,
        )
    if "overall" not in health:
        raise SprintError(
            "'health_assessment' requires 'overall' field",
            file=file,
        )
    valid_health = ["healthy", "warning", "degraded"]
    if health["overall"] not in valid_health:
        raise SprintError(
            f"Invalid health assessment: '{health['overall']}'."
            f" Must be one of: {', '.join(valid_health)}",
            file=file,
        )


def validate_phase_13_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> None:
    """Validate retrospective/feedback-intake body fields.

    Phase 13 has two outputs:
      - retrospective.yaml (13a): requires 'sprint_summary'
      - feedback-intake.yaml (13b): requires 'synthesis'

    Args:
        data: Full YAML data for the phase.
        file: Source file path for error reporting.

    Raises:
        SprintError: If required body fields are missing or malformed.
    """
    has_summary = "sprint_summary" in data
    has_synthesis = "synthesis" in data

    if not has_summary and not has_synthesis:
        raise SprintError(
            "Phase 13 requires 'sprint_summary' (retrospective)"
            " or 'synthesis' (feedback-intake) field",
            file=file,
        )

    if has_summary and not isinstance(data["sprint_summary"], dict):
        raise SprintError(
            "'sprint_summary' must be a mapping",
            file=file,
        )
    if has_synthesis and not isinstance(data["synthesis"], dict):
        raise SprintError(
            "'synthesis' must be a mapping",
            file=file,
        )


PHASE_BODY_VALIDATORS: dict[int, Callable[..., None]] = {
    1: validate_phase_1_body,
    2: validate_phase_2_body,
    3: validate_phase_3_body,
    4: validate_phase_4_body,
    5: validate_phase_5_body,
    6: validate_phase_6_body,
    7: validate_phase_7_body,
    8: validate_phase_8_body,
    9: validate_phase_9_body,
    10: validate_phase_10_body,
    11: validate_phase_11_body,
    12: validate_phase_12_body,
    13: validate_phase_13_body,
}


# ---------------------------------------------------------------------------
# Public API: load and validate a phase output
# ---------------------------------------------------------------------------


def load_phase_output(yaml_path: Path | str) -> HandoffEnvelope:
    """Load and validate a sprint phase YAML file.

    Three-stage validation:
        1. YAML parse — catches syntax errors
        2. Structure mapping — maps to HandoffEnvelope dataclass
        3. Semantic validation — checks phase/name, depends_on, timestamps

    Args:
        yaml_path: Path to the .sprint/*.yaml file.

    Returns:
        Validated HandoffEnvelope.

    Raises:
        SprintError: On any validation failure.
    """
    yaml_path = Path(yaml_path)
    file_str = str(yaml_path)

    # Stage 1: YAML parse
    data = _load_yaml(yaml_path)

    # Stage 2: Structure mapping
    envelope = _parse_envelope(data, file_str)

    # Stage 3: Semantic validation
    validate_envelope(envelope, file_str)

    # Phase-specific body validation
    validator = PHASE_BODY_VALIDATORS.get(envelope.phase)
    if validator:
        validator(data, file_str)

    return envelope


# ---------------------------------------------------------------------------
# Sprint meta: load and validate
# ---------------------------------------------------------------------------


def _parse_phase_log_entry(
    entry: dict[str, Any],
    index: int,
    file: Optional[str] = None,
) -> PhaseLogEntry:
    """Parse a single phase log entry.

    Args:
        entry: Raw dictionary for one phase_log item.
        index: Index in the phase_log list (for error messages).
        file: Source file path for error reporting.

    Returns:
        Parsed PhaseLogEntry.

    Raises:
        SprintError: If required fields are missing.
    """
    if not isinstance(entry, dict):
        raise SprintError(
            f"phase_log[{index}] must be a mapping",
            file=file,
        )
    for key in ("phase", "phase_name", "status", "started_at", "output_file"):
        if key not in entry:
            raise SprintError(
                f"phase_log[{index}] missing required field: '{key}'",
                file=file,
            )

    return PhaseLogEntry(
        phase=entry["phase"],
        phase_name=entry["phase_name"],
        status=entry["status"],
        started_at=str(entry["started_at"]),
        completed_at=str(entry["completed_at"]) if entry.get("completed_at") else None,
        output_file=entry["output_file"],
        validated=bool(entry.get("validated", False)),
    )


def load_sprint_meta(meta_path: Path | str) -> SprintMeta:
    """Load and validate sprint-meta.yaml.

    Args:
        meta_path: Path to .sprint/sprint-meta.yaml.

    Returns:
        Validated SprintMeta.

    Raises:
        SprintError: On any validation failure.
    """
    meta_path = Path(meta_path)
    file_str = str(meta_path)

    # Stage 1: YAML parse
    data = _load_yaml(meta_path)

    # Stage 2: Structure mapping
    required_fields = [
        "sprint_id",
        "started",
        "velocity_mode",
        "requirements",
        "current_phase",
        "status",
    ]
    for key in required_fields:
        if key not in data:
            raise SprintError(
                f"Missing required field in sprint-meta.yaml: '{key}'",
                file=file_str,
            )

    phase_log_raw = data.get("phase_log", [])
    if not isinstance(phase_log_raw, list):
        raise SprintError("'phase_log' must be a list", file=file_str)

    phase_log = [
        _parse_phase_log_entry(entry, i, file_str)
        for i, entry in enumerate(phase_log_raw)
    ]

    meta = SprintMeta(
        sprint_id=str(data["sprint_id"]),
        schema_version=str(data.get("_schema_version", "0.0")),
        started=str(data["started"]),
        velocity_mode=str(data["velocity_mode"]),
        requirements=str(data["requirements"]),
        current_phase=int(data["current_phase"]),
        status=str(data["status"]),
        phase_log=phase_log,
        phases_failed=list(data.get("phases_failed", [])),
        retry_count=int(data.get("retry_count", 0)),
        revision_cycles=int(data.get("revision_cycles", 0)),
        last_error=data.get("last_error"),
    )

    # Stage 3: Semantic validation
    if meta.current_phase not in VALID_PHASES:
        raise SprintError(
            f"Invalid current_phase: {meta.current_phase}. Must be 1-13.",
            file=file_str,
        )
    if meta.status not in VALID_META_STATUSES:
        raise SprintError(
            f"Invalid status: '{meta.status}'."
            f" Must be one of: {', '.join(VALID_META_STATUSES)}",
            file=file_str,
        )
    if meta.velocity_mode not in VALID_VELOCITY_MODES:
        raise SprintError(
            f"Invalid velocity_mode: '{meta.velocity_mode}'."
            f" Must be one of: {', '.join(VALID_VELOCITY_MODES)}",
            file=file_str,
        )

    _validate_iso_timestamp(meta.started, file_str)

    return meta


# ---------------------------------------------------------------------------
# Directory validator
# ---------------------------------------------------------------------------


def validate_sprint_dir(sprint_dir: Path | str) -> list[SprintError]:
    """Validate all YAML files in a .sprint/ directory.

    Args:
        sprint_dir: Path to the .sprint/ directory.

    Returns:
        List of SprintErrors found. Empty list means all valid.
    """
    sprint_dir = Path(sprint_dir)
    errors: list[SprintError] = []

    if not sprint_dir.is_dir():
        errors.append(SprintError(
            f"Not a directory: {sprint_dir}",
            file=str(sprint_dir),
            error_type="dir_missing",
        ))
        return errors

    # Validate sprint-meta.yaml if present
    meta_path = sprint_dir / "sprint-meta.yaml"
    if meta_path.exists():
        try:
            load_sprint_meta(meta_path)
        except SprintError as e:
            errors.append(e)

    # Validate phase output files
    for phase_num, filename in PHASE_OUTPUT_FILES.items():
        filepath = sprint_dir / filename
        if not filepath.exists():
            continue  # Missing files are OK (phase not yet run)
        try:
            load_phase_output(filepath)
        except SprintError as e:
            errors.append(e)

    return errors


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def _write_sprint_meta(meta: SprintMeta, meta_path: Path) -> None:
    """Write sprint-meta.yaml from a SprintMeta dataclass.

    Args:
        meta: SprintMeta to serialize.
        meta_path: Output path.
    """
    phase_log_data = [
        {
            "phase": entry.phase,
            "phase_name": entry.phase_name,
            "status": entry.status,
            "started_at": entry.started_at,
            "completed_at": entry.completed_at,
            "output_file": entry.output_file,
            "validated": entry.validated,
        }
        for entry in meta.phase_log
    ]

    data: dict[str, Any] = {
        "sprint_id": meta.sprint_id,
        "_schema_version": meta.schema_version,
        "started": meta.started,
        "velocity_mode": meta.velocity_mode,
        "requirements": meta.requirements,
        "current_phase": meta.current_phase,
        "status": meta.status,
        "phase_log": phase_log_data,
        "phases_failed": meta.phases_failed,
        "retry_count": meta.retry_count,
        "revision_cycles": meta.revision_cycles,
        "last_error": meta.last_error,
    }

    content = yaml.dump(data, default_flow_style=False, sort_keys=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=meta_path.parent, suffix=".tmp", prefix=meta_path.stem
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        Path(tmp_path).replace(meta_path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def rollback_to_phase(sprint_dir: Path | str, target_phase: int) -> None:
    """Roll back sprint state to a given phase.

    Deletes all output files for phases after target_phase and resets
    current_phase in sprint-meta.yaml. Used by the smart router and
    the revision cycle, not as a standalone subcommand.

    Args:
        sprint_dir: Path to the .sprint/ directory.
        target_phase: Phase number to rollback to (1-13).

    Raises:
        SprintError: If target_phase is invalid or meta cannot be loaded.
    """
    sprint_dir = Path(sprint_dir)
    meta_path = sprint_dir / "sprint-meta.yaml"

    if target_phase not in VALID_PHASES:
        raise SprintError(
            f"Invalid target phase: {target_phase}. Must be 1-13."
        )

    meta = load_sprint_meta(meta_path)

    if target_phase > meta.current_phase:
        raise SprintError(
            f"Cannot rollback to phase {target_phase}."
            f" Current phase is {meta.current_phase}."
        )

    # Delete output files for phases after target
    for phase_num in range(target_phase + 1, 14):
        filename = PHASE_OUTPUT_FILES.get(phase_num)
        if filename:
            filepath = sprint_dir / filename
            if filepath.exists():
                filepath.unlink()

    # Also delete feedback-intake.yaml (phase 13b) if rolling back before 13
    if target_phase < 13:
        feedback_path = sprint_dir / "feedback-intake.yaml"
        if feedback_path.exists():
            feedback_path.unlink()

    # Delete Phase 6 execution log when rolling back before implementation
    if target_phase < 6:
        exec_log_path = sprint_dir / "execution-log.md"
        if exec_log_path.exists():
            exec_log_path.unlink()

    # Update meta
    meta.current_phase = target_phase
    meta.phase_log = [e for e in meta.phase_log if e.phase <= target_phase]
    meta.status = "in_progress"
    meta.last_error = None

    _write_sprint_meta(meta, meta_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Validate a .sprint/ directory from the command line.

    Returns:
        Exit code: 0 for success, 1 for validation errors, 2 for usage errors.
    """
    if len(sys.argv) > 2:
        print("Usage: python -m scripts.sprint.validate [sprint_dir]", file=sys.stderr)
        return 2

    sprint_dir = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".sprint")

    if not sprint_dir.is_dir():
        print(
            json.dumps({"error": "dir_missing", "message": f"Not a directory: {sprint_dir}"}),
            file=sys.stderr,
        )
        return 2

    errors = validate_sprint_dir(sprint_dir)

    if not errors:
        print(f"OK: {sprint_dir} is valid")
        return 0

    for error in errors:
        print(json.dumps(error.to_json()), file=sys.stderr)

    print(f"FAIL: {len(errors)} error(s) found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
