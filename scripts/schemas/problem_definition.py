"""Problem-definition handoff schema validation.

Validates .problem-definition/handoff.yaml against the structured contract
between /problem-definition and /requirements-engineering. Follows the
three-stage validation pattern from scripts/sprint/validate.py.

Usage:
    python -m scripts.schemas.problem_definition [dir]

Examples:
    python -m scripts.schemas.problem_definition .problem-definition/
    python -m scripts.schemas.problem_definition
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from scripts.schemas.common import (
    SchemaError,
    SignalsBlock,
    load_yaml,
    parse_signals,
    validate_confidence,
    validate_iso_timestamp,
    validate_status,
)


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CLASSIFICATION_TYPES: list[str] = [
    "tame",
    "complicated",
    "wicked",
    "mess",
]

VALID_OWNER_PRIORITIES: list[str] = [
    "primary",
    "secondary",
    "affected",
]

VALID_GAP_DIMENSIONS: list[str] = [
    "what",
    "where",
    "when",
    "who",
    "how_much",
]

VALID_DEFINED_BY: list[str] = [
    "agent",
    "user",
    "collaborative",
]

HANDOFF_FILENAME = "handoff.yaml"


# ---------------------------------------------------------------------------
# Dataclasses — Problem Definition Body
# ---------------------------------------------------------------------------


@dataclass
class Concern:
    """A single concern from the problem situation."""

    concern: str
    source: str


@dataclass
class ProblemSituation:
    """Step 1 output: the explored problem situation."""

    context: str
    concerns: list[Concern]
    interconnections: str
    prior_attempts: str


@dataclass
class ProblemClassification:
    """Step 2 output: problem type classification."""

    type: str
    evidence: list[str]
    implication: str


@dataclass
class Frame:
    """A single problem frame (current, alternative, or selected)."""

    description: str
    held_by: Optional[str] = None
    reveals: Optional[str] = None
    includes: Optional[str] = None
    excludes: Optional[str] = None


@dataclass
class AlternativeFrame:
    """An alternative problem frame."""

    frame: str
    reveals: str


@dataclass
class SelectedFrame:
    """The selected working frame."""

    description: str
    includes: str
    excludes: str


@dataclass
class ProblemFraming:
    """Step 3 output: problem framing analysis."""

    current_frame: Frame
    alternative_frames: list[AlternativeFrame]
    selected_frame: SelectedFrame


@dataclass
class ProblemOwner:
    """Step 4 output: a person/role who experiences the problem."""

    who: str
    experience: str
    cost: str
    priority: str


@dataclass
class GapDimension:
    """A single dimension of the IS/IS-NOT gap analysis."""

    dimension: str
    is_current: str
    is_not_desired: str
    gap: str


@dataclass
class ProblemDefinitionBody:
    """Step 5 output: the crystallized problem definition."""

    gap_analysis: list[GapDimension]
    problem_statement: str
    cost_of_problem: str
    worth_solving: bool
    worth_solving_rationale: str


@dataclass
class ExcludedClass:
    """A solution class that was excluded."""

    solution_class: str
    reason: str


@dataclass
class SolutionSpace:
    """Step 6 output: bounded solution space."""

    classes_considered: list[str]
    classes_excluded: list[ExcludedClass]
    trade_offs: list[str]
    existing_partial_solutions: list[str]
    recommended_next_step: str


@dataclass
class QualityGate:
    """The 7 quality checks for problem definition completeness."""

    solution_free: bool
    specific: bool
    measurable: bool
    owners_identified: bool
    worth_solving_explicit: bool
    frame_stated: bool
    solution_space_bounded: bool
    all_passed: bool


@dataclass
class Provenance:
    """Metadata about how the problem definition was produced."""

    frameworks_applied: list[str]
    defined_by: str
    boundary_critique: Optional[str] = None
    iterations: int = 0


@dataclass
class ProblemDefinitionHandoff:
    """Complete problem-definition handoff, paralleling HandoffEnvelope."""

    schema_version: str
    phase: str
    phase_name: str
    skill: str
    status: str
    timestamp: str
    depends_on: Optional[str]
    summary: str
    outputs: list[str]
    open_issues: list[str]
    signals: SignalsBlock
    problem_situation: ProblemSituation
    problem_classification: ProblemClassification
    problem_framing: ProblemFraming
    problem_owners: list[ProblemOwner]
    problem_definition: ProblemDefinitionBody
    solution_space: SolutionSpace
    quality_gate: QualityGate
    provenance: Provenance


# ---------------------------------------------------------------------------
# Stage 2: Structure mapping
# ---------------------------------------------------------------------------


def _require_field(
    data: dict[str, Any],
    key: str,
    file: Optional[str] = None,
    parent: str = "",
) -> Any:
    """Get a required field from a dictionary.

    Args:
        data: Dictionary to read from.
        key: Key to look up.
        file: Source file path for error reporting.
        parent: Parent key name for error messages.

    Returns:
        The value.

    Raises:
        SchemaError: If key is missing.
    """
    if key not in data:
        location = f"'{parent}.{key}'" if parent else f"'{key}'"
        raise SchemaError(
            f"Missing required field: {location}",
            file=file,
        )
    return data[key]


def _require_bool_field(
    data: dict[str, Any],
    key: str,
    file: Optional[str] = None,
    parent: str = "",
) -> bool:
    """Get a required boolean field from a dictionary."""
    value = _require_field(data, key, file, parent)
    if not isinstance(value, bool):
        location = f"'{parent}.{key}'" if parent else f"'{key}'"
        raise SchemaError(f"{location} must be a boolean", file=file)
    return value


def _validate_list_field(
    data: dict[str, Any],
    key: str,
    file: Optional[str] = None,
) -> list:
    """Get an optional list field, normalising None to [] and rejecting non-lists."""
    raw = data.get(key, [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise SchemaError(f"'{key}' must be a list", file=file)
    return raw


def _parse_concerns(
    raw: list[Any],
    file: Optional[str] = None,
) -> list[Concern]:
    """Parse a list of concern dictionaries."""
    concerns = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SchemaError(
                f"concerns[{i}] must be a mapping",
                file=file,
            )
        concerns.append(
            Concern(
                concern=str(_require_field(item, "concern", file, f"concerns[{i}]")),
                source=str(_require_field(item, "source", file, f"concerns[{i}]")),
            )
        )
    return concerns


def _parse_problem_situation(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> ProblemSituation:
    """Parse problem_situation section."""
    section = _require_field(data, "problem_situation", file)
    if not isinstance(section, dict):
        raise SchemaError("'problem_situation' must be a mapping", file=file)

    raw_concerns = _require_field(section, "concerns", file, "problem_situation")
    if not isinstance(raw_concerns, list):
        raise SchemaError(
            "'problem_situation.concerns' must be a list", file=file
        )

    return ProblemSituation(
        context=str(_require_field(section, "context", file, "problem_situation")),
        concerns=_parse_concerns(raw_concerns, file),
        interconnections=str(
            _require_field(section, "interconnections", file, "problem_situation")
        ),
        prior_attempts=str(section.get("prior_attempts", "")),
    )


def _parse_problem_classification(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> ProblemClassification:
    """Parse problem_classification section."""
    section = _require_field(data, "problem_classification", file)
    if not isinstance(section, dict):
        raise SchemaError("'problem_classification' must be a mapping", file=file)

    raw_evidence = _require_field(
        section, "evidence", file, "problem_classification"
    )
    if not isinstance(raw_evidence, list):
        raise SchemaError(
            "'problem_classification.evidence' must be a list", file=file
        )

    return ProblemClassification(
        type=str(
            _require_field(section, "type", file, "problem_classification")
        ),
        evidence=[str(e) for e in raw_evidence],
        implication=str(
            _require_field(section, "implication", file, "problem_classification")
        ),
    )


def _parse_problem_framing(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> ProblemFraming:
    """Parse problem_framing section."""
    section = _require_field(data, "problem_framing", file)
    if not isinstance(section, dict):
        raise SchemaError("'problem_framing' must be a mapping", file=file)

    # Current frame
    raw_current = _require_field(
        section, "current_frame", file, "problem_framing"
    )
    if not isinstance(raw_current, dict):
        raise SchemaError(
            "'problem_framing.current_frame' must be a mapping", file=file
        )
    current_frame = Frame(
        description=str(
            _require_field(raw_current, "description", file, "current_frame")
        ),
        held_by=str(raw_current.get("held_by", "")),
    )

    # Alternative frames
    raw_alts = _require_field(
        section, "alternative_frames", file, "problem_framing"
    )
    if not isinstance(raw_alts, list):
        raise SchemaError(
            "'problem_framing.alternative_frames' must be a list", file=file
        )
    alt_frames = []
    for i, item in enumerate(raw_alts):
        if not isinstance(item, dict):
            raise SchemaError(
                f"alternative_frames[{i}] must be a mapping", file=file
            )
        alt_frames.append(
            AlternativeFrame(
                frame=str(
                    _require_field(item, "frame", file, f"alternative_frames[{i}]")
                ),
                reveals=str(
                    _require_field(
                        item, "reveals", file, f"alternative_frames[{i}]"
                    )
                ),
            )
        )

    # Selected frame
    raw_selected = _require_field(
        section, "selected_frame", file, "problem_framing"
    )
    if not isinstance(raw_selected, dict):
        raise SchemaError(
            "'problem_framing.selected_frame' must be a mapping", file=file
        )
    selected_frame = SelectedFrame(
        description=str(
            _require_field(raw_selected, "description", file, "selected_frame")
        ),
        includes=str(
            _require_field(raw_selected, "includes", file, "selected_frame")
        ),
        excludes=str(
            _require_field(raw_selected, "excludes", file, "selected_frame")
        ),
    )

    return ProblemFraming(
        current_frame=current_frame,
        alternative_frames=alt_frames,
        selected_frame=selected_frame,
    )


def _parse_problem_owners(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> list[ProblemOwner]:
    """Parse problem_owners section."""
    raw = _require_field(data, "problem_owners", file)
    if not isinstance(raw, list):
        raise SchemaError("'problem_owners' must be a list", file=file)
    if len(raw) == 0:
        raise SchemaError("'problem_owners' must not be empty", file=file)

    owners = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SchemaError(
                f"problem_owners[{i}] must be a mapping", file=file
            )
        owners.append(
            ProblemOwner(
                who=str(
                    _require_field(item, "who", file, f"problem_owners[{i}]")
                ),
                experience=str(
                    _require_field(
                        item, "experience", file, f"problem_owners[{i}]"
                    )
                ),
                cost=str(
                    _require_field(item, "cost", file, f"problem_owners[{i}]")
                ),
                priority=str(
                    _require_field(
                        item, "priority", file, f"problem_owners[{i}]"
                    )
                ),
            )
        )
    return owners


def _parse_gap_analysis(
    raw: list[Any],
    file: Optional[str] = None,
) -> list[GapDimension]:
    """Parse gap_analysis list."""
    if not isinstance(raw, list):
        raise SchemaError(
            "'problem_definition.gap_analysis' must be a list", file=file
        )

    dimensions = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SchemaError(
                f"gap_analysis[{i}] must be a mapping", file=file
            )
        dimensions.append(
            GapDimension(
                dimension=str(
                    _require_field(item, "dimension", file, f"gap_analysis[{i}]")
                ),
                is_current=str(
                    _require_field(
                        item, "is_current", file, f"gap_analysis[{i}]"
                    )
                ),
                is_not_desired=str(
                    _require_field(
                        item, "is_not_desired", file, f"gap_analysis[{i}]"
                    )
                ),
                gap=str(
                    _require_field(item, "gap", file, f"gap_analysis[{i}]")
                ),
            )
        )
    return dimensions


def _parse_problem_definition_body(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> ProblemDefinitionBody:
    """Parse problem_definition section."""
    section = _require_field(data, "problem_definition", file)
    if not isinstance(section, dict):
        raise SchemaError("'problem_definition' must be a mapping", file=file)

    raw_gap = _require_field(
        section, "gap_analysis", file, "problem_definition"
    )

    return ProblemDefinitionBody(
        gap_analysis=_parse_gap_analysis(raw_gap, file),
        problem_statement=str(
            _require_field(
                section, "problem_statement", file, "problem_definition"
            )
        ),
        cost_of_problem=str(
            _require_field(
                section, "cost_of_problem", file, "problem_definition"
            )
        ),
        worth_solving=_require_bool_field(
            section, "worth_solving", file, "problem_definition"
        ),
        worth_solving_rationale=str(
            _require_field(
                section, "worth_solving_rationale", file, "problem_definition"
            )
        ),
    )


def _parse_solution_space(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> SolutionSpace:
    """Parse solution_space section."""
    section = _require_field(data, "solution_space", file)
    if not isinstance(section, dict):
        raise SchemaError("'solution_space' must be a mapping", file=file)

    raw_excluded = section.get("classes_excluded", [])
    if not isinstance(raw_excluded, list):
        raise SchemaError(
            "'solution_space.classes_excluded' must be a list", file=file
        )

    excluded = []
    for i, item in enumerate(raw_excluded):
        if isinstance(item, dict):
            # Accept both "class" (YAML key) and "solution_class" (Python field name)
            # since "class" is a reserved word in Python
            solution_class = item.get("class", item.get("solution_class"))
            if not solution_class:
                raise SchemaError(
                    f"classes_excluded[{i}].class is required",
                    file=file,
                )
            excluded.append(
                ExcludedClass(
                    solution_class=str(solution_class),
                    reason=str(item.get("reason", "")),
                )
            )
        elif isinstance(item, str):
            excluded.append(ExcludedClass(solution_class=item, reason=""))
        else:
            raise SchemaError(
                f"classes_excluded[{i}] must be a mapping or string",
                file=file,
            )

    raw_considered = _require_field(
        section, "classes_considered", file, "solution_space"
    )
    if not isinstance(raw_considered, list):
        raise SchemaError(
            "'solution_space.classes_considered' must be a list", file=file
        )

    raw_trade_offs = section.get("trade_offs", [])
    if raw_trade_offs is None:
        raw_trade_offs = []
    if not isinstance(raw_trade_offs, list):
        raise SchemaError("'solution_space.trade_offs' must be a list", file=file)

    raw_partial = section.get("existing_partial_solutions", [])
    if raw_partial is None:
        raw_partial = []
    if not isinstance(raw_partial, list):
        raise SchemaError(
            "'solution_space.existing_partial_solutions' must be a list",
            file=file,
        )

    return SolutionSpace(
        classes_considered=[str(c) for c in raw_considered],
        classes_excluded=excluded,
        trade_offs=[str(t) for t in raw_trade_offs],
        existing_partial_solutions=[str(s) for s in raw_partial],
        recommended_next_step=str(
            _require_field(
                section, "recommended_next_step", file, "solution_space"
            )
        ),
    )


def _parse_quality_gate(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> QualityGate:
    """Parse quality_gate section."""
    section = _require_field(data, "quality_gate", file)
    if not isinstance(section, dict):
        raise SchemaError("'quality_gate' must be a mapping", file=file)

    return QualityGate(
        solution_free=_require_bool_field(section, "solution_free", file, "quality_gate"),
        specific=_require_bool_field(section, "specific", file, "quality_gate"),
        measurable=_require_bool_field(section, "measurable", file, "quality_gate"),
        owners_identified=_require_bool_field(section, "owners_identified", file, "quality_gate"),
        worth_solving_explicit=_require_bool_field(section, "worth_solving_explicit", file, "quality_gate"),
        frame_stated=_require_bool_field(section, "frame_stated", file, "quality_gate"),
        solution_space_bounded=_require_bool_field(section, "solution_space_bounded", file, "quality_gate"),
        all_passed=_require_bool_field(section, "all_passed", file, "quality_gate"),
    )


def _parse_provenance(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> Provenance:
    """Parse provenance section."""
    section = _require_field(data, "provenance", file)
    if not isinstance(section, dict):
        raise SchemaError("'provenance' must be a mapping", file=file)

    raw_frameworks = _require_field(
        section, "frameworks_applied", file, "provenance"
    )
    if not isinstance(raw_frameworks, list):
        raise SchemaError(
            "'provenance.frameworks_applied' must be a list", file=file
        )

    raw_iterations = section.get("iterations", 0)
    if raw_iterations is None:
        raw_iterations = 0
    try:
        iterations = int(raw_iterations)
    except (TypeError, ValueError):
        raise SchemaError("'provenance.iterations' must be an integer", file=file)

    return Provenance(
        frameworks_applied=[str(f) for f in raw_frameworks],
        defined_by=str(
            _require_field(section, "defined_by", file, "provenance")
        ),
        boundary_critique=section.get("boundary_critique"),
        iterations=iterations,
    )


def parse_handoff(
    data: dict[str, Any],
    file: Optional[str] = None,
) -> ProblemDefinitionHandoff:
    """Map raw YAML dictionary to ProblemDefinitionHandoff dataclass.

    Stage 2 of validation: structural mapping.

    Args:
        data: Raw YAML data.
        file: Source file path for error reporting.

    Returns:
        Parsed ProblemDefinitionHandoff.

    Raises:
        SchemaError: If required fields are missing or malformed.
    """
    # Envelope fields
    required_envelope = ["phase", "phase_name", "skill", "status", "timestamp", "summary"]
    for key in required_envelope:
        _require_field(data, key, file)

    return ProblemDefinitionHandoff(
        schema_version=str(data.get("_schema_version", "0.0")),
        phase=str(data["phase"]),
        phase_name=str(data["phase_name"]),
        skill=str(data["skill"]),
        status=str(data["status"]),
        timestamp=str(data["timestamp"]),
        depends_on=data.get("depends_on"),
        summary=str(data["summary"]),
        outputs=[str(o) for o in _validate_list_field(data, "outputs", file)],
        open_issues=[str(i) for i in _validate_list_field(data, "open_issues", file)],
        signals=parse_signals(data, file),
        problem_situation=_parse_problem_situation(data, file),
        problem_classification=_parse_problem_classification(data, file),
        problem_framing=_parse_problem_framing(data, file),
        problem_owners=_parse_problem_owners(data, file),
        problem_definition=_parse_problem_definition_body(data, file),
        solution_space=_parse_solution_space(data, file),
        quality_gate=_parse_quality_gate(data, file),
        provenance=_parse_provenance(data, file),
    )


# ---------------------------------------------------------------------------
# Stage 3: Semantic validation
# ---------------------------------------------------------------------------


def validate_handoff(
    handoff: ProblemDefinitionHandoff,
    file: Optional[str] = None,
) -> None:
    """Validate semantic correctness of a problem-definition handoff.

    Stage 3 of validation: semantic checks.

    Args:
        handoff: Parsed handoff dataclass.
        file: Source file path for error reporting.

    Raises:
        SchemaError: If any semantic validation fails.
    """
    # 1. Schema version must match
    if handoff.schema_version != CURRENT_SCHEMA_VERSION:
        raise SchemaError(
            f"_schema_version must be '{CURRENT_SCHEMA_VERSION}',"
            f" got '{handoff.schema_version}'",
            file=file,
        )

    # 2. Phase must be "problem_definition"
    if handoff.phase != "problem_definition":
        raise SchemaError(
            f"phase must be 'problem_definition', got '{handoff.phase}'",
            file=file,
        )

    # 3. Skill must be "problem-definition"
    if handoff.skill != "problem-definition":
        raise SchemaError(
            f"skill must be 'problem-definition', got '{handoff.skill}'",
            file=file,
        )

    # 4. Status must be a valid value
    validate_status(handoff.status, file)

    # 5. Timestamp must be valid ISO 8601
    validate_iso_timestamp(handoff.timestamp, file)

    # 6. Confidence must be a valid value
    validate_confidence(handoff.signals.confidence, file)

    # 7. Classification type must be valid
    if handoff.problem_classification.type not in VALID_CLASSIFICATION_TYPES:
        raise SchemaError(
            f"Invalid classification type: '{handoff.problem_classification.type}'."
            f" Must be one of: {', '.join(VALID_CLASSIFICATION_TYPES)}",
            file=file,
        )

    # 8. Owner priorities must be valid
    for i, owner in enumerate(handoff.problem_owners):
        if owner.priority not in VALID_OWNER_PRIORITIES:
            raise SchemaError(
                f"Invalid priority for problem_owners[{i}]:"
                f" '{owner.priority}'."
                f" Must be one of: {', '.join(VALID_OWNER_PRIORITIES)}",
                file=file,
            )

    # 9. Gap analysis dimensions must be valid
    for i, dim in enumerate(handoff.problem_definition.gap_analysis):
        if dim.dimension not in VALID_GAP_DIMENSIONS:
            raise SchemaError(
                f"Invalid gap dimension: '{dim.dimension}'."
                f" Must be one of: {', '.join(VALID_GAP_DIMENSIONS)}",
                file=file,
            )

    # 10. At least 3 of 5 standard gap dimensions should be present
    dims_present = {d.dimension for d in handoff.problem_definition.gap_analysis}
    if len(dims_present) < 3:
        raise SchemaError(
            f"gap_analysis has {len(dims_present)} dimensions,"
            f" expected at least 3 of 5"
            f" ({', '.join(VALID_GAP_DIMENSIONS)})",
            file=file,
        )

    # 11. Problem statement must be non-empty
    if not handoff.problem_definition.problem_statement.strip():
        raise SchemaError(
            "problem_statement must not be empty",
            file=file,
        )

    # 12. If worth_solving is False, recommended_next_step should not be
    #     /requirements-engineering
    if (
        not handoff.problem_definition.worth_solving
        and "/requirements-engineering" in handoff.solution_space.recommended_next_step
    ):
        raise SchemaError(
            "problem is marked as not worth solving but recommended_next_step"
            " points to /requirements-engineering",
            file=file,
        )

    # 13. quality_gate.all_passed must match individual gate fields
    individual_gates = [
        handoff.quality_gate.solution_free,
        handoff.quality_gate.specific,
        handoff.quality_gate.measurable,
        handoff.quality_gate.owners_identified,
        handoff.quality_gate.worth_solving_explicit,
        handoff.quality_gate.frame_stated,
        handoff.quality_gate.solution_space_bounded,
    ]
    expected_all_passed = all(individual_gates)
    if handoff.quality_gate.all_passed != expected_all_passed:
        raise SchemaError(
            f"quality_gate.all_passed is {handoff.quality_gate.all_passed}"
            f" but individual gates compute to {expected_all_passed}",
            file=file,
        )

    # 14. If status is "complete", quality_gate.all_passed must be True
    if handoff.status == "complete" and not handoff.quality_gate.all_passed:
        raise SchemaError(
            "status is 'complete' but quality_gate.all_passed is False",
            file=file,
        )

    # 15. signals.pass should align with quality_gate.all_passed
    if handoff.signals.pass_ != handoff.quality_gate.all_passed:
        raise SchemaError(
            f"signals.pass ({handoff.signals.pass_}) does not match"
            f" quality_gate.all_passed ({handoff.quality_gate.all_passed})",
            file=file,
        )

    # 16. defined_by must be a valid value
    if handoff.provenance.defined_by not in VALID_DEFINED_BY:
        raise SchemaError(
            f"Invalid defined_by: '{handoff.provenance.defined_by}'."
            f" Must be one of: {', '.join(VALID_DEFINED_BY)}",
            file=file,
        )

    # 17. At least one concern must exist
    if len(handoff.problem_situation.concerns) == 0:
        raise SchemaError(
            "problem_situation.concerns must not be empty",
            file=file,
        )

    # 18. At least one alternative frame
    if len(handoff.problem_framing.alternative_frames) == 0:
        raise SchemaError(
            "problem_framing.alternative_frames must not be empty",
            file=file,
        )

    # 19. At least one solution class considered
    if len(handoff.solution_space.classes_considered) == 0:
        raise SchemaError(
            "solution_space.classes_considered must not be empty",
            file=file,
        )


# ---------------------------------------------------------------------------
# Full validation pipeline
# ---------------------------------------------------------------------------


def validate_file(yaml_path: Path) -> ProblemDefinitionHandoff:
    """Run all three validation stages on a handoff file.

    Args:
        yaml_path: Path to the YAML handoff file.

    Returns:
        Validated ProblemDefinitionHandoff dataclass.

    Raises:
        SchemaError: If any stage fails.
    """
    file_str = str(yaml_path)

    # Stage 1: Parse
    data = load_yaml(yaml_path)

    # Stage 2: Structure
    handoff = parse_handoff(data, file_str)

    # Stage 3: Semantics
    validate_handoff(handoff, file_str)

    return handoff


def validate_directory(dir_path: Path) -> ProblemDefinitionHandoff:
    """Validate a .problem-definition/ directory.

    Looks for handoff.yaml inside the directory.

    Args:
        dir_path: Path to the problem-definition directory.

    Returns:
        Validated ProblemDefinitionHandoff dataclass.

    Raises:
        SchemaError: If validation fails.
    """
    handoff_path = dir_path / HANDOFF_FILENAME
    return validate_file(handoff_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for problem-definition validation.

    Returns:
        0 on success, 1 on validation error, 2 on usage error.
    """
    if len(sys.argv) > 2:
        print(
            "Usage: python -m scripts.schemas.problem_definition [dir]",
            file=sys.stderr,
        )
        return 2

    target = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".problem-definition")

    try:
        if target.is_file():
            handoff = validate_file(target)
        else:
            handoff = validate_directory(target)
    except SchemaError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print("OK: Problem definition validated successfully")
    print(f"  Status: {handoff.status}")
    print(f"  Classification: {handoff.problem_classification.type}")
    print(f"  Problem owners: {len(handoff.problem_owners)}")
    print(f"  Gap dimensions: {len(handoff.problem_definition.gap_analysis)}")
    print(f"  Quality gate: {'PASSED' if handoff.quality_gate.all_passed else 'FAILED'}")
    print(f"  Worth solving: {'Yes' if handoff.problem_definition.worth_solving else 'No'}")
    return 0
