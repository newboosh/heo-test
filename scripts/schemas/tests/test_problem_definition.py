"""Tests for problem-definition handoff schema validation.

Follows the sprint test patterns (scripts/sprint/tests/test_validate.py)
with pytest and AAA structure. Covers all three validation stages.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.schemas.common import SchemaError
from scripts.schemas.problem_definition import (
    CURRENT_SCHEMA_VERSION,
    VALID_CLASSIFICATION_TYPES,
    VALID_DEFINED_BY,
    VALID_GAP_DIMENSIONS,
    VALID_OWNER_PRIORITIES,
    ProblemDefinitionHandoff,
    parse_handoff,
    validate_file,
    validate_handoff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> Path:
    """Write a YAML file and return its path."""
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def _minimal_handoff(**overrides) -> dict:
    """Return a minimal valid problem-definition handoff."""
    base = {
        "_schema_version": CURRENT_SCHEMA_VERSION,
        "phase": "problem_definition",
        "phase_name": "Problem Definition",
        "skill": "problem-definition",
        "status": "complete",
        "timestamp": "2026-02-14T10:00:00Z",
        "depends_on": None,
        "summary": "Test problem definition.",
        "outputs": [".problem-definition/handoff.yaml"],
        "open_issues": [],
        "signals": {
            "pass": True,
            "confidence": "high",
            "blockers": [],
        },
        "problem_situation": {
            "context": "Test context for the situation.",
            "concerns": [
                {"concern": "First concern", "source": "User interview"},
                {"concern": "Second concern", "source": "Code analysis"},
            ],
            "interconnections": "Concerns are related.",
            "prior_attempts": "None.",
        },
        "problem_classification": {
            "type": "tame",
            "evidence": ["Problem can be clearly defined"],
            "implication": "Standard engineering applies.",
        },
        "problem_framing": {
            "current_frame": {
                "description": "This is a performance problem.",
                "held_by": "Development team",
            },
            "alternative_frames": [
                {
                    "frame": "This is a workflow problem",
                    "reveals": "Users are doing unnecessary steps",
                },
            ],
            "selected_frame": {
                "description": "Performance frame selected.",
                "includes": "Response time and throughput",
                "excludes": "UI redesign",
            },
        },
        "problem_owners": [
            {
                "who": "API consumers",
                "experience": "Slow response times during peak hours",
                "cost": "Lost revenue from timeouts",
                "priority": "primary",
            },
        ],
        "problem_definition": {
            "gap_analysis": [
                {
                    "dimension": "what",
                    "is_current": "API responds in 5s",
                    "is_not_desired": "API should respond in < 500ms",
                    "gap": "10x slower than target",
                },
                {
                    "dimension": "when",
                    "is_current": "During peak hours (9-11am)",
                    "is_not_desired": "Should be fast at all times",
                    "gap": "Peak-hour degradation",
                },
                {
                    "dimension": "how_much",
                    "is_current": "95th percentile at 5s",
                    "is_not_desired": "95th percentile < 500ms",
                    "gap": "4.5s delta",
                },
            ],
            "problem_statement": "API response time degrades to 5s during peak hours.",
            "cost_of_problem": "Lost revenue from user abandonment.",
            "worth_solving": True,
            "worth_solving_rationale": "Direct revenue impact.",
        },
        "solution_space": {
            "classes_considered": ["Caching", "Query optimization"],
            "classes_excluded": [
                {"class": "Hardware scaling", "reason": "Budget constraint"},
            ],
            "trade_offs": ["Simplicity vs. cache invalidation complexity"],
            "existing_partial_solutions": ["Existing Redis instance"],
            "recommended_next_step": "/requirements-engineering",
        },
        "quality_gate": {
            "solution_free": True,
            "specific": True,
            "measurable": True,
            "owners_identified": True,
            "worth_solving_explicit": True,
            "frame_stated": True,
            "solution_space_bounded": True,
            "all_passed": True,
        },
        "provenance": {
            "frameworks_applied": ["Kepner-Tregoe", "IEEE 29148"],
            "defined_by": "agent",
            "boundary_critique": None,
            "iterations": 0,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Stage 1: YAML Parsing
# ---------------------------------------------------------------------------


class TestYAMLParsing:
    """Stage 1: file loading and YAML parsing."""

    def test_valid_file_loads(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path / "handoff.yaml", _minimal_handoff())
        # Should not raise
        handoff = validate_file(path)
        assert isinstance(handoff, ProblemDefinitionHandoff)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SchemaError, match="File not found"):
            validate_file(tmp_path / "nonexistent.yaml")

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "handoff.yaml"
        path.write_text("")
        with pytest.raises(SchemaError, match="File is empty"):
            validate_file(path)

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "handoff.yaml"
        path.write_text("{ invalid: yaml: content")
        with pytest.raises(SchemaError, match="Invalid YAML"):
            validate_file(path)

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "handoff.yaml"
        path.write_text("- just\n- a\n- list\n")
        with pytest.raises(SchemaError, match="must be a mapping"):
            validate_file(path)


# ---------------------------------------------------------------------------
# Stage 2: Structure Mapping
# ---------------------------------------------------------------------------


class TestStructureMapping:
    """Stage 2: dataclass construction from raw YAML."""

    def test_minimal_handoff_parses(self) -> None:
        data = _minimal_handoff()
        handoff = parse_handoff(data)
        assert handoff.phase == "problem_definition"
        assert handoff.skill == "problem-definition"
        assert handoff.status == "complete"
        assert len(handoff.problem_owners) == 1
        assert handoff.problem_owners[0].who == "API consumers"

    def test_missing_envelope_field_raises(self) -> None:
        data = _minimal_handoff()
        del data["phase"]
        with pytest.raises(SchemaError, match="'phase'"):
            parse_handoff(data)

    def test_missing_problem_situation_raises(self) -> None:
        data = _minimal_handoff()
        del data["problem_situation"]
        with pytest.raises(SchemaError, match="'problem_situation'"):
            parse_handoff(data)

    def test_missing_problem_classification_raises(self) -> None:
        data = _minimal_handoff()
        del data["problem_classification"]
        with pytest.raises(SchemaError, match="'problem_classification'"):
            parse_handoff(data)

    def test_missing_problem_framing_raises(self) -> None:
        data = _minimal_handoff()
        del data["problem_framing"]
        with pytest.raises(SchemaError, match="'problem_framing'"):
            parse_handoff(data)

    def test_missing_problem_owners_raises(self) -> None:
        data = _minimal_handoff()
        del data["problem_owners"]
        with pytest.raises(SchemaError, match="'problem_owners'"):
            parse_handoff(data)

    def test_empty_problem_owners_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_owners"] = []
        with pytest.raises(SchemaError, match="must not be empty"):
            parse_handoff(data)

    def test_missing_problem_definition_raises(self) -> None:
        data = _minimal_handoff()
        del data["problem_definition"]
        with pytest.raises(SchemaError, match="'problem_definition'"):
            parse_handoff(data)

    def test_missing_solution_space_raises(self) -> None:
        data = _minimal_handoff()
        del data["solution_space"]
        with pytest.raises(SchemaError, match="'solution_space'"):
            parse_handoff(data)

    def test_missing_quality_gate_raises(self) -> None:
        data = _minimal_handoff()
        del data["quality_gate"]
        with pytest.raises(SchemaError, match="'quality_gate'"):
            parse_handoff(data)

    def test_missing_provenance_raises(self) -> None:
        data = _minimal_handoff()
        del data["provenance"]
        with pytest.raises(SchemaError, match="'provenance'"):
            parse_handoff(data)

    def test_missing_signals_raises(self) -> None:
        data = _minimal_handoff()
        del data["signals"]
        with pytest.raises(SchemaError, match="'signals'"):
            parse_handoff(data)

    def test_concern_missing_fields_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_situation"]["concerns"] = [{"concern": "no source"}]
        with pytest.raises(SchemaError, match="'concerns\\[0\\].source'"):
            parse_handoff(data)

    def test_gap_dimension_missing_fields_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_definition"]["gap_analysis"] = [
            {"dimension": "what", "is_current": "x"}
        ]
        with pytest.raises(SchemaError, match="gap_analysis"):
            parse_handoff(data)

    def test_classes_excluded_string_format(self) -> None:
        """classes_excluded accepts plain strings as well as dicts."""
        data = _minimal_handoff()
        data["solution_space"]["classes_excluded"] = ["Hardware scaling"]
        handoff = parse_handoff(data)
        assert handoff.solution_space.classes_excluded[0].solution_class == "Hardware scaling"

    def test_multiple_problem_owners(self) -> None:
        data = _minimal_handoff()
        data["problem_owners"].append(
            {
                "who": "DevOps team",
                "experience": "Alert fatigue from timeouts",
                "cost": "On-call burden",
                "priority": "secondary",
            }
        )
        handoff = parse_handoff(data)
        assert len(handoff.problem_owners) == 2


# ---------------------------------------------------------------------------
# Stage 3: Semantic Validation
# ---------------------------------------------------------------------------


class TestSemanticValidation:
    """Stage 3: semantic correctness checks."""

    def test_valid_handoff_passes(self) -> None:
        data = _minimal_handoff()
        handoff = parse_handoff(data)
        # Should not raise
        validate_handoff(handoff)

    def test_wrong_phase_raises(self) -> None:
        data = _minimal_handoff(phase="something_else")
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="problem_definition"):
            validate_handoff(handoff)

    def test_wrong_skill_raises(self) -> None:
        data = _minimal_handoff(skill="wrong-skill")
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="problem-definition"):
            validate_handoff(handoff)

    def test_invalid_status_raises(self) -> None:
        data = _minimal_handoff(status="in_progress")
        # Must also fix quality gate and signals for consistency
        data["quality_gate"]["all_passed"] = False
        data["signals"]["pass"] = False
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="Invalid status"):
            validate_handoff(handoff)

    def test_invalid_timestamp_raises(self) -> None:
        data = _minimal_handoff(timestamp="not-a-date")
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="ISO 8601"):
            validate_handoff(handoff)

    def test_invalid_classification_type_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_classification"]["type"] = "invalid_type"
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="classification type"):
            validate_handoff(handoff)

    @pytest.mark.parametrize("valid_type", VALID_CLASSIFICATION_TYPES)
    def test_all_classification_types_accepted(self, valid_type: str) -> None:
        data = _minimal_handoff()
        data["problem_classification"]["type"] = valid_type
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise

    def test_invalid_owner_priority_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_owners"][0]["priority"] = "critical"
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="Invalid priority"):
            validate_handoff(handoff)

    @pytest.mark.parametrize("valid_priority", VALID_OWNER_PRIORITIES)
    def test_all_owner_priorities_accepted(self, valid_priority: str) -> None:
        data = _minimal_handoff()
        data["problem_owners"][0]["priority"] = valid_priority
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise

    def test_invalid_gap_dimension_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_definition"]["gap_analysis"][0]["dimension"] = "invalid"
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="Invalid gap dimension"):
            validate_handoff(handoff)

    def test_too_few_gap_dimensions_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_definition"]["gap_analysis"] = [
            {
                "dimension": "what",
                "is_current": "x",
                "is_not_desired": "y",
                "gap": "z",
            },
            {
                "dimension": "when",
                "is_current": "x",
                "is_not_desired": "y",
                "gap": "z",
            },
        ]
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="at least 3"):
            validate_handoff(handoff)

    def test_empty_problem_statement_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_definition"]["problem_statement"] = "   "
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="problem_statement must not be empty"):
            validate_handoff(handoff)

    def test_not_worth_solving_with_re_next_step_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_definition"]["worth_solving"] = False
        data["problem_definition"]["worth_solving_rationale"] = "Cost too high."
        data["solution_space"]["recommended_next_step"] = "/requirements-engineering"
        # Adjust quality gate to match
        data["quality_gate"]["worth_solving_explicit"] = True
        data["quality_gate"]["all_passed"] = True
        data["signals"]["pass"] = True
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="not worth solving"):
            validate_handoff(handoff)

    def test_invalid_defined_by_raises(self) -> None:
        data = _minimal_handoff()
        data["provenance"]["defined_by"] = "robot"
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="Invalid defined_by"):
            validate_handoff(handoff)

    @pytest.mark.parametrize("valid_by", VALID_DEFINED_BY)
    def test_all_defined_by_values_accepted(self, valid_by: str) -> None:
        data = _minimal_handoff()
        data["provenance"]["defined_by"] = valid_by
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise

    def test_empty_concerns_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_situation"]["concerns"] = []
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="concerns must not be empty"):
            validate_handoff(handoff)

    def test_empty_alternative_frames_raises(self) -> None:
        data = _minimal_handoff()
        data["problem_framing"]["alternative_frames"] = []
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="alternative_frames must not be empty"):
            validate_handoff(handoff)

    def test_empty_classes_considered_raises(self) -> None:
        data = _minimal_handoff()
        data["solution_space"]["classes_considered"] = []
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="classes_considered must not be empty"):
            validate_handoff(handoff)


# ---------------------------------------------------------------------------
# Quality Gate
# ---------------------------------------------------------------------------


class TestQualityGate:
    """Quality gate consistency checks."""

    def test_all_passed_matches_individual_gates(self) -> None:
        data = _minimal_handoff()
        data["quality_gate"]["all_passed"] = False
        # But all individual gates are True
        data["signals"]["pass"] = False
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="quality_gate.all_passed"):
            validate_handoff(handoff)

    def test_complete_status_requires_all_passed(self) -> None:
        data = _minimal_handoff()
        data["quality_gate"]["solution_free"] = False
        data["quality_gate"]["all_passed"] = False
        data["signals"]["pass"] = False
        data["status"] = "complete"
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="quality_gate.all_passed is False"):
            validate_handoff(handoff)

    def test_draft_status_allows_failed_gate(self) -> None:
        data = _minimal_handoff()
        data["status"] = "draft"
        data["quality_gate"]["solution_free"] = False
        data["quality_gate"]["all_passed"] = False
        data["signals"]["pass"] = False
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise

    def test_signals_pass_must_match_quality_gate(self) -> None:
        data = _minimal_handoff()
        # All quality gates pass, but signals.pass is False
        data["signals"]["pass"] = False
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="signals.pass"):
            validate_handoff(handoff)

    @pytest.mark.parametrize(
        "gate_field",
        [
            "solution_free",
            "specific",
            "measurable",
            "owners_identified",
            "worth_solving_explicit",
            "frame_stated",
            "solution_space_bounded",
        ],
    )
    def test_single_gate_failure_detected(self, gate_field: str) -> None:
        """If one gate fails but all_passed is True, validation catches it."""
        data = _minimal_handoff()
        data["quality_gate"][gate_field] = False
        # all_passed still True — should fail
        handoff = parse_handoff(data)
        with pytest.raises(SchemaError, match="quality_gate.all_passed"):
            validate_handoff(handoff)


# ---------------------------------------------------------------------------
# End-to-End File Validation
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: file → parse → structure → semantics."""

    def test_valid_file_validates(self, tmp_path: Path) -> None:
        path = _write_yaml(tmp_path / "handoff.yaml", _minimal_handoff())
        handoff = validate_file(path)
        assert handoff.problem_definition.problem_statement.strip() != ""
        assert handoff.quality_gate.all_passed is True

    def test_invalid_file_raises(self, tmp_path: Path) -> None:
        data = _minimal_handoff()
        data["problem_classification"]["type"] = "bogus"
        path = _write_yaml(tmp_path / "handoff.yaml", data)
        with pytest.raises(SchemaError):
            validate_file(path)

    def test_directory_validation(self, tmp_path: Path) -> None:
        pd_dir = tmp_path / ".problem-definition"
        pd_dir.mkdir()
        _write_yaml(pd_dir / "handoff.yaml", _minimal_handoff())
        from scripts.schemas.problem_definition import validate_directory

        handoff = validate_directory(pd_dir)
        assert handoff.phase == "problem_definition"

    def test_all_five_gap_dimensions(self) -> None:
        """A handoff with all 5 standard dimensions validates."""
        data = _minimal_handoff()
        data["problem_definition"]["gap_analysis"] = [
            {
                "dimension": dim,
                "is_current": f"current-{dim}",
                "is_not_desired": f"desired-{dim}",
                "gap": f"gap-{dim}",
            }
            for dim in VALID_GAP_DIMENSIONS
        ]
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise
        assert len(handoff.problem_definition.gap_analysis) == 5

    def test_wicked_problem_validates(self) -> None:
        """A wicked problem with draft status and failed gates validates."""
        data = _minimal_handoff()
        data["status"] = "draft"
        data["problem_classification"]["type"] = "wicked"
        data["problem_classification"]["evidence"] = [
            "No definitive formulation",
            "Definition depends on solution",
        ]
        data["quality_gate"]["measurable"] = False
        data["quality_gate"]["all_passed"] = False
        data["signals"]["pass"] = False
        handoff = parse_handoff(data)
        validate_handoff(handoff)  # Should not raise
