"""Tests for sprint YAML schema validation.

Follows catalog test patterns (scripts/catalog/tests/test_config.py)
with pytest and AAA structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.sprint.validate import (
    CURRENT_SCHEMA_VERSION,
    HandoffEnvelope,
    SprintError,
    SprintMeta,
    load_phase_output,
    load_sprint_meta,
    rollback_to_phase,
    validate_sprint_dir,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> Path:
    """Write a YAML file and return its path."""
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


def _minimal_envelope(phase: int = 1, **overrides) -> dict:
    """Return a minimal valid handoff envelope for the given phase."""
    from scripts.sprint.validate import DEPENDS_ON_MAP, PHASE_NAME_MAP

    phase_names_to_roles = {
        1: "developer",
        2: "product_manager",
        3: "ux_designer",
        4: "tech_lead",
        5: "tech_lead",
        6: "developer_agent",
        7: "senior_developer",
        8: "qa_engineer",
        9: "security_engineer",
        10: "devops",
        11: "release_manager",
        12: "sre",
        13: "scrum_master",
    }
    base = {
        "phase": phase,
        "phase_name": PHASE_NAME_MAP[phase],
        "role": phase_names_to_roles.get(phase, "developer"),
        "status": "complete",
        "timestamp": "2026-02-09T12:00:00Z",
        "depends_on": DEPENDS_ON_MAP[phase],
        "summary": "Test summary",
        "outputs": [f".sprint/test-{phase}.yaml"],
        "open_issues": [],
        "signals": {
            "pass": True,
            "confidence": "high",
            "blockers": [],
        },
        "_schema_version": CURRENT_SCHEMA_VERSION,
    }
    base.update(overrides)
    return base


def _phase_1_data(**overrides) -> dict:
    """Return valid phase 1 data."""
    data = _minimal_envelope(1)
    data["what"] = "Build a new feature"
    data.update(overrides)
    return data


def _phase_5_data(**overrides) -> dict:
    """Return valid phase 5 data."""
    data = _minimal_envelope(5)
    data["sprint_backlog"] = [
        {"id": "TASK-001", "title": "First task", "type": "feature"},
        {"id": "TASK-002", "title": "Second task", "type": "test"},
    ]
    data["task_order"] = ["TASK-001", "TASK-002"]
    data["summary"] = "Backlog summary"
    data.update(overrides)
    return data


def _phase_7_data(**overrides) -> dict:
    """Return valid phase 7 (code review) data."""
    data = _minimal_envelope(7)
    data["findings"] = [
        {
            "reviewer": "code-reviewer",
            "severity": "info",
            "description": "Minor style issue",
            "status": "resolved",
        },
    ]
    data.update(overrides)
    return data


def _phase_8_data(**overrides) -> dict:
    """Return valid phase 8 (QA) data."""
    data = _minimal_envelope(8)
    data["test_results"] = {"total": 10, "passing": 10, "failing": 0}
    data.update(overrides)
    return data


def _phase_9_data(**overrides) -> dict:
    """Return valid phase 9 (security review) data."""
    data = _minimal_envelope(9)
    data["findings"] = [
        {
            "category": "injection",
            "severity": "none",
            "description": "Input properly sanitized",
            "status": "not_applicable",
        },
    ]
    data.update(overrides)
    return data


def _phase_11_data(**overrides) -> dict:
    """Return valid phase 11 (merge) data."""
    data = _minimal_envelope(11)
    data["gate_decision"] = {
        "verdict": "SHIP",
        "rationale": "All signals green",
        "blockers": [],
    }
    data.update(overrides)
    return data


def _phase_12_data(**overrides) -> dict:
    """Return valid phase 12 (monitoring) data."""
    data = _minimal_envelope(12)
    data["health_assessment"] = {"overall": "healthy", "concerns": []}
    data.update(overrides)
    return data


def _phase_13_data(**overrides) -> dict:
    """Return valid phase 13 (retrospective) data."""
    data = _minimal_envelope(13)
    data["sprint_summary"] = {
        "tasks_planned": 4,
        "tasks_completed": 4,
        "duration_hours": 1.5,
    }
    data.update(overrides)
    return data


def _minimal_meta(**overrides) -> dict:
    """Return minimal valid sprint-meta.yaml data."""
    base = {
        "sprint_id": "abc123",
        "_schema_version": CURRENT_SCHEMA_VERSION,
        "started": "2026-02-09T10:00:00Z",
        "velocity_mode": "autonomous",
        "requirements": "Build a feature",
        "current_phase": 1,
        "status": "in_progress",
        "phase_log": [],
        "phases_failed": [],
        "retry_count": 0,
        "revision_cycles": 0,
        "last_error": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestSprintError
# ---------------------------------------------------------------------------


class TestSprintError:
    """Tests for SprintError class (mirrors TestConfigError)."""

    def test_message_is_stored(self) -> None:
        """Error stores its message."""
        # Arrange & Act
        err = SprintError("something broke")

        # Assert
        assert err.message == "something broke"
        assert str(err) == "something broke"

    def test_file_and_line_info(self) -> None:
        """Error includes file and line metadata."""
        # Arrange & Act
        err = SprintError("bad field", file="input.yaml", line=5)

        # Assert
        assert err.file == "input.yaml"
        assert err.line == 5
        assert "input.yaml" in str(err)
        assert "line: 5" in str(err)

    def test_to_json(self) -> None:
        """Error serializes to JSON."""
        # Arrange
        err = SprintError("invalid", file="x.yaml", error_type="yaml_parse")

        # Act
        result = err.to_json()

        # Assert
        assert result["error"] == "yaml_parse"
        assert result["message"] == "invalid"
        assert result["file"] == "x.yaml"

    def test_to_json_minimal(self) -> None:
        """Error serializes without optional fields."""
        # Arrange & Act
        result = SprintError("msg").to_json()

        # Assert
        assert result == {"error": "sprint_invalid", "message": "msg"}


# ---------------------------------------------------------------------------
# TestLoadPhaseOutput
# ---------------------------------------------------------------------------


class TestLoadPhaseOutput:
    """Tests for loading and validating phase output YAML."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises SprintError with file_missing type."""
        # Arrange
        path = tmp_path / "nonexistent.yaml"

        # Act & Assert
        with pytest.raises(SprintError, match="File not found") as exc_info:
            load_phase_output(path)
        assert exc_info.value.error_type == "file_missing"

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML syntax raises SprintError."""
        # Arrange
        path = tmp_path / "bad.yaml"
        path.write_text("{{invalid yaml")

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid YAML"):
            load_phase_output(path)

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        """YAML that parses to a list raises SprintError."""
        # Arrange
        path = tmp_path / "list.yaml"
        path.write_text("- item1\n- item2\n")

        # Act & Assert
        with pytest.raises(SprintError, match="must be a mapping"):
            load_phase_output(path)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        """Empty file raises SprintError."""
        # Arrange
        path = tmp_path / "empty.yaml"
        path.write_text("")

        # Act & Assert
        with pytest.raises(SprintError, match="empty"):
            load_phase_output(path)

    def test_valid_phase_1_loads(self, tmp_path: Path) -> None:
        """Valid phase 1 file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "input.yaml", _phase_1_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert isinstance(envelope, HandoffEnvelope)
        assert envelope.phase == 1
        assert envelope.phase_name == "intake"
        assert envelope.role == "developer"
        assert envelope.signals.pass_ is True

    def test_valid_phase_5_loads(self, tmp_path: Path) -> None:
        """Valid phase 5 file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "backlog.yaml", _phase_5_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 5
        assert envelope.phase_name == "backlog"

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        """Missing required envelope field raises SprintError."""
        # Arrange
        data = _phase_1_data()
        del data["phase_name"]
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="Missing required field.*phase_name"):
            load_phase_output(path)

    def test_invalid_phase_number_raises(self, tmp_path: Path) -> None:
        """Phase number outside 1-13 raises SprintError."""
        # Arrange
        data = _phase_1_data(phase=99)
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid phase: 99"):
            load_phase_output(path)

    def test_mismatched_phase_name_raises(self, tmp_path: Path) -> None:
        """Phase name not matching phase number raises SprintError."""
        # Arrange
        data = _phase_1_data(phase_name="wrong_name")
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="doesn't match"):
            load_phase_output(path)

    def test_invalid_timestamp_raises(self, tmp_path: Path) -> None:
        """Invalid timestamp format raises SprintError."""
        # Arrange
        data = _phase_1_data(timestamp="not-a-date")
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid ISO 8601 timestamp"):
            load_phase_output(path)

    def test_wrong_depends_on_raises(self, tmp_path: Path) -> None:
        """Wrong depends_on value raises SprintError."""
        # Arrange
        data = _phase_1_data(depends_on="should_be_null")
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="depends_on should be"):
            load_phase_output(path)

    def test_missing_signals_raises(self, tmp_path: Path) -> None:
        """Missing signals block raises SprintError."""
        # Arrange
        data = _phase_1_data()
        del data["signals"]
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="signals"):
            load_phase_output(path)

    def test_failed_status_without_blockers_raises(self, tmp_path: Path) -> None:
        """Failed status with no blockers or open_issues raises SprintError."""
        # Arrange
        data = _phase_1_data(
            status="failed",
            open_issues=[],
        )
        data["signals"]["blockers"] = []
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must have non-empty"):
            load_phase_output(path)


# ---------------------------------------------------------------------------
# TestPhaseBodyValidation
# ---------------------------------------------------------------------------


class TestPhaseBodyValidation:
    """Tests for phase-specific body validators."""

    def test_phase_1_missing_what_raises(self, tmp_path: Path) -> None:
        """Phase 1 without 'what' field raises SprintError."""
        # Arrange
        data = _minimal_envelope(1)  # No 'what' field
        path = _write_yaml(tmp_path / "input.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'what'"):
            load_phase_output(path)

    def test_phase_5_missing_backlog_raises(self, tmp_path: Path) -> None:
        """Phase 5 without 'sprint_backlog' raises SprintError."""
        # Arrange
        data = _minimal_envelope(5)  # No sprint_backlog
        path = _write_yaml(tmp_path / "backlog.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'sprint_backlog'"):
            load_phase_output(path)

    def test_phase_5_empty_backlog_raises(self, tmp_path: Path) -> None:
        """Phase 5 with empty sprint_backlog raises SprintError."""
        # Arrange
        data = _minimal_envelope(5, sprint_backlog=[])
        path = _write_yaml(tmp_path / "backlog.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="non-empty list"):
            load_phase_output(path)

    def test_phase_5_task_missing_id_raises(self, tmp_path: Path) -> None:
        """Phase 5 task without 'id' raises SprintError."""
        # Arrange
        data = _minimal_envelope(5, sprint_backlog=[{"title": "No ID"}])
        path = _write_yaml(tmp_path / "backlog.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="missing 'id'"):
            load_phase_output(path)

    def test_phase_2_missing_epic_raises(self, tmp_path: Path) -> None:
        """Phase 2 without 'epic' raises SprintError."""
        # Arrange
        data = _minimal_envelope(2)
        path = _write_yaml(tmp_path / "product.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'epic'"):
            load_phase_output(path)

    def test_phase_3_missing_ux_raises(self, tmp_path: Path) -> None:
        """Phase 3 without 'ux_requirements' raises SprintError."""
        # Arrange
        data = _minimal_envelope(3)
        path = _write_yaml(tmp_path / "design.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'ux_requirements'"):
            load_phase_output(path)

    def test_phase_4_missing_architecture_raises(self, tmp_path: Path) -> None:
        """Phase 4 without 'architecture' raises SprintError."""
        # Arrange
        data = _minimal_envelope(4)
        path = _write_yaml(tmp_path / "technical.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'architecture'"):
            load_phase_output(path)


# ---------------------------------------------------------------------------
# TestPhase7To13BodyValidation
# ---------------------------------------------------------------------------


class TestPhase7To13BodyValidation:
    """Tests for phase 7-13 body validators."""

    def test_phase_7_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 7 file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "review-code.yaml", _phase_7_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 7
        assert envelope.phase_name == "code_review"

    def test_phase_7_missing_findings_raises(self, tmp_path: Path) -> None:
        """Phase 7 without 'findings' raises SprintError."""
        # Arrange
        data = _minimal_envelope(7)
        path = _write_yaml(tmp_path / "review-code.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'findings'"):
            load_phase_output(path)

    def test_phase_7_findings_not_list_raises(self, tmp_path: Path) -> None:
        """Phase 7 with non-list findings raises SprintError."""
        # Arrange
        data = _minimal_envelope(7, findings="not a list")
        path = _write_yaml(tmp_path / "review-code.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must be a list"):
            load_phase_output(path)

    def test_phase_8_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 8 (QA) file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "qa-report.yaml", _phase_8_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 8
        assert envelope.phase_name == "qa"

    def test_phase_8_missing_test_results_raises(self, tmp_path: Path) -> None:
        """Phase 8 (QA) without 'test_results' raises SprintError."""
        # Arrange
        data = _minimal_envelope(8)
        path = _write_yaml(tmp_path / "qa-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'test_results'"):
            load_phase_output(path)

    def test_phase_8_test_results_not_mapping_raises(self, tmp_path: Path) -> None:
        """Phase 8 (QA) with non-mapping test_results raises SprintError."""
        # Arrange
        data = _minimal_envelope(8, test_results=[1, 2, 3])
        path = _write_yaml(tmp_path / "qa-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must be a mapping"):
            load_phase_output(path)

    def test_phase_9_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 9 (security review) file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "review-security.yaml", _phase_9_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 9
        assert envelope.phase_name == "security_review"

    def test_phase_9_missing_findings_raises(self, tmp_path: Path) -> None:
        """Phase 9 (security review) without 'findings' raises SprintError."""
        # Arrange
        data = _minimal_envelope(9)
        path = _write_yaml(tmp_path / "review-security.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'findings'"):
            load_phase_output(path)

    def test_phase_9_findings_not_list_raises(self, tmp_path: Path) -> None:
        """Phase 9 (security review) with non-list findings raises SprintError."""
        # Arrange
        data = _minimal_envelope(9, findings="not a list")
        path = _write_yaml(tmp_path / "review-security.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must be a list"):
            load_phase_output(path)

    def test_phase_10_missing_pipeline_raises(self, tmp_path: Path) -> None:
        """Phase 10 without 'pipeline' raises SprintError."""
        # Arrange
        data = _minimal_envelope(10)
        path = _write_yaml(tmp_path / "ci-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'pipeline'"):
            load_phase_output(path)

    def test_phase_10_pipeline_not_mapping_raises(self, tmp_path: Path) -> None:
        """Phase 10 with non-mapping pipeline raises SprintError."""
        # Arrange
        data = _minimal_envelope(10, pipeline="not a mapping")
        path = _write_yaml(tmp_path / "ci-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must be a mapping"):
            load_phase_output(path)

    def test_phase_11_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 11 file loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "merge-report.yaml", _phase_11_data())

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 11
        assert envelope.phase_name == "merge"

    def test_phase_11_missing_gate_decision_raises(self, tmp_path: Path) -> None:
        """Phase 11 without 'gate_decision' raises SprintError."""
        # Arrange
        data = _minimal_envelope(11)
        path = _write_yaml(tmp_path / "merge-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'gate_decision'"):
            load_phase_output(path)

    def test_phase_11_missing_verdict_raises(self, tmp_path: Path) -> None:
        """Phase 11 gate_decision without 'verdict' raises SprintError."""
        # Arrange
        data = _minimal_envelope(11, gate_decision={"rationale": "test"})
        path = _write_yaml(tmp_path / "merge-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'verdict'"):
            load_phase_output(path)

    def test_phase_11_invalid_verdict_raises(self, tmp_path: Path) -> None:
        """Phase 11 with invalid verdict value raises SprintError."""
        # Arrange
        data = _minimal_envelope(11, gate_decision={"verdict": "MAYBE"})
        path = _write_yaml(tmp_path / "merge-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid gate verdict"):
            load_phase_output(path)

    def test_phase_12_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 12 file loads successfully."""
        # Arrange
        path = _write_yaml(
            tmp_path / "monitoring-report.yaml", _phase_12_data()
        )

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 12
        assert envelope.phase_name == "monitoring"

    def test_phase_12_missing_health_raises(self, tmp_path: Path) -> None:
        """Phase 12 without 'health_assessment' raises SprintError."""
        # Arrange
        data = _minimal_envelope(12)
        path = _write_yaml(tmp_path / "monitoring-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'health_assessment'"):
            load_phase_output(path)

    def test_phase_12_missing_overall_raises(self, tmp_path: Path) -> None:
        """Phase 12 health_assessment without 'overall' raises."""
        # Arrange
        data = _minimal_envelope(12, health_assessment={"concerns": []})
        path = _write_yaml(tmp_path / "monitoring-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'overall'"):
            load_phase_output(path)

    def test_phase_12_invalid_health_raises(self, tmp_path: Path) -> None:
        """Phase 12 with invalid health value raises SprintError."""
        # Arrange
        data = _minimal_envelope(12, health_assessment={"overall": "fine"})
        path = _write_yaml(tmp_path / "monitoring-report.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid health assessment"):
            load_phase_output(path)

    def test_phase_13_valid_loads(self, tmp_path: Path) -> None:
        """Valid phase 13 file loads successfully."""
        # Arrange
        path = _write_yaml(
            tmp_path / "retrospective.yaml", _phase_13_data()
        )

        # Act
        envelope = load_phase_output(path)

        # Assert
        assert envelope.phase == 13
        assert envelope.phase_name == "retrospective"

    def test_phase_13_missing_sprint_summary_raises(self, tmp_path: Path) -> None:
        """Phase 13 without 'sprint_summary' raises SprintError."""
        # Arrange
        data = _minimal_envelope(13)
        path = _write_yaml(tmp_path / "retrospective.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="requires 'sprint_summary'"):
            load_phase_output(path)

    def test_phase_13_sprint_summary_not_mapping_raises(self, tmp_path: Path) -> None:
        """Phase 13 with non-mapping sprint_summary raises SprintError."""
        # Arrange
        data = _minimal_envelope(13, sprint_summary="not a mapping")
        path = _write_yaml(tmp_path / "retrospective.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="must be a mapping"):
            load_phase_output(path)


# ---------------------------------------------------------------------------
# TestValidateSprintDir
# ---------------------------------------------------------------------------


class TestValidateSprintDir:
    """Tests for directory-level validation."""

    def test_empty_dir_returns_no_errors(self, tmp_path: Path) -> None:
        """Empty directory with no files is valid (no phases run yet)."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()

        # Act
        errors = validate_sprint_dir(sprint_dir)

        # Assert
        assert errors == []

    def test_valid_sprint_returns_no_errors(self, tmp_path: Path) -> None:
        """Directory with valid phase files returns no errors."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "input.yaml", _phase_1_data())
        _write_yaml(sprint_dir / "sprint-meta.yaml", _minimal_meta())

        # Act
        errors = validate_sprint_dir(sprint_dir)

        # Assert
        assert errors == []

    def test_invalid_file_returns_errors(self, tmp_path: Path) -> None:
        """Directory with an invalid file returns errors."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "input.yaml", {"bad": "data"})

        # Act
        errors = validate_sprint_dir(sprint_dir)

        # Assert
        assert len(errors) > 0

    def test_nonexistent_dir_returns_error(self, tmp_path: Path) -> None:
        """Nonexistent directory returns dir_missing error."""
        # Arrange
        sprint_dir = tmp_path / "nope"

        # Act
        errors = validate_sprint_dir(sprint_dir)

        # Assert
        assert len(errors) == 1
        assert errors[0].error_type == "dir_missing"


# ---------------------------------------------------------------------------
# TestSprintMeta
# ---------------------------------------------------------------------------


class TestSprintMeta:
    """Tests for sprint-meta.yaml loading and validation."""

    def test_load_valid_meta(self, tmp_path: Path) -> None:
        """Valid sprint-meta.yaml loads successfully."""
        # Arrange
        path = _write_yaml(tmp_path / "sprint-meta.yaml", _minimal_meta())

        # Act
        meta = load_sprint_meta(path)

        # Assert
        assert isinstance(meta, SprintMeta)
        assert meta.sprint_id == "abc123"
        assert meta.velocity_mode == "autonomous"
        assert meta.current_phase == 1

    def test_phase_log_tracks_completions(self, tmp_path: Path) -> None:
        """Phase log entries are parsed correctly."""
        # Arrange
        data = _minimal_meta(
            current_phase=2,
            phase_log=[
                {
                    "phase": 1,
                    "phase_name": "intake",
                    "status": "complete",
                    "started_at": "2026-02-09T10:00:00Z",
                    "completed_at": "2026-02-09T10:30:00Z",
                    "output_file": "input.yaml",
                    "validated": True,
                },
            ],
        )
        path = _write_yaml(tmp_path / "sprint-meta.yaml", data)

        # Act
        meta = load_sprint_meta(path)

        # Assert
        assert len(meta.phase_log) == 1
        assert meta.phase_log[0].phase == 1
        assert meta.phase_log[0].validated is True

    def test_missing_meta_raises(self, tmp_path: Path) -> None:
        """Missing sprint-meta.yaml raises SprintError."""
        # Arrange
        path = tmp_path / "sprint-meta.yaml"

        # Act & Assert
        with pytest.raises(SprintError, match="File not found"):
            load_sprint_meta(path)

    def test_invalid_velocity_mode_raises(self, tmp_path: Path) -> None:
        """Invalid velocity mode raises SprintError."""
        # Arrange
        data = _minimal_meta(velocity_mode="turbo")
        path = _write_yaml(tmp_path / "sprint-meta.yaml", data)

        # Act & Assert
        with pytest.raises(SprintError, match="velocity_mode"):
            load_sprint_meta(path)


# ---------------------------------------------------------------------------
# TestRollback
# ---------------------------------------------------------------------------


class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback_deletes_forward_files(self, tmp_path: Path) -> None:
        """Rollback removes files for phases after target."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "input.yaml", _phase_1_data())
        _write_yaml(
            sprint_dir / "product.yaml",
            _minimal_envelope(2, epic={"title": "T"}, user_stories=[{"id": "US-001"}]),
        )
        _write_yaml(
            sprint_dir / "sprint-meta.yaml",
            _minimal_meta(
                current_phase=2,
                phase_log=[
                    {
                        "phase": 1, "phase_name": "intake", "status": "complete",
                        "started_at": "2026-02-09T10:00:00Z",
                        "completed_at": "2026-02-09T10:30:00Z",
                        "output_file": "input.yaml", "validated": True,
                    },
                    {
                        "phase": 2, "phase_name": "refinement", "status": "complete",
                        "started_at": "2026-02-09T10:30:00Z",
                        "completed_at": "2026-02-09T11:00:00Z",
                        "output_file": "product.yaml", "validated": True,
                    },
                ],
            ),
        )

        # Act
        rollback_to_phase(sprint_dir, 1)

        # Assert
        assert (sprint_dir / "input.yaml").exists()
        assert not (sprint_dir / "product.yaml").exists()

    def test_rollback_resets_current_phase(self, tmp_path: Path) -> None:
        """Rollback updates current_phase in sprint-meta.yaml."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "input.yaml", _phase_1_data())
        _write_yaml(
            sprint_dir / "sprint-meta.yaml",
            _minimal_meta(
                current_phase=3,
                phase_log=[
                    {
                        "phase": 1, "phase_name": "intake", "status": "complete",
                        "started_at": "2026-02-09T10:00:00Z",
                        "completed_at": "2026-02-09T10:30:00Z",
                        "output_file": "input.yaml", "validated": True,
                    },
                ],
            ),
        )

        # Act
        rollback_to_phase(sprint_dir, 1)

        # Assert
        meta = load_sprint_meta(sprint_dir / "sprint-meta.yaml")
        assert meta.current_phase == 1
        assert meta.status == "in_progress"

    def test_rollback_to_invalid_phase_raises(self, tmp_path: Path) -> None:
        """Rollback to phase 0 or 14 raises SprintError."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "sprint-meta.yaml", _minimal_meta())

        # Act & Assert
        with pytest.raises(SprintError, match="Invalid target phase"):
            rollback_to_phase(sprint_dir, 0)

    def test_rollback_to_future_phase_raises(self, tmp_path: Path) -> None:
        """Rollback to a phase after current_phase raises SprintError."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(
            sprint_dir / "sprint-meta.yaml",
            _minimal_meta(current_phase=2),
        )

        # Act & Assert
        with pytest.raises(SprintError, match="Cannot rollback"):
            rollback_to_phase(sprint_dir, 5)

    def test_rollback_preserves_earlier_phases(self, tmp_path: Path) -> None:
        """Rollback preserves files for phases at or before target."""
        # Arrange
        sprint_dir = tmp_path / ".sprint"
        sprint_dir.mkdir()
        _write_yaml(sprint_dir / "input.yaml", _phase_1_data())
        _write_yaml(
            sprint_dir / "sprint-meta.yaml",
            _minimal_meta(
                current_phase=1,
                phase_log=[
                    {
                        "phase": 1, "phase_name": "intake", "status": "complete",
                        "started_at": "2026-02-09T10:00:00Z",
                        "completed_at": "2026-02-09T10:30:00Z",
                        "output_file": "input.yaml", "validated": True,
                    },
                ],
            ),
        )

        # Act
        rollback_to_phase(sprint_dir, 1)

        # Assert
        assert (sprint_dir / "input.yaml").exists()
        meta = load_sprint_meta(sprint_dir / "sprint-meta.yaml")
        assert len(meta.phase_log) == 1
