"""Tests for constants and enums: structural integrity checks."""

from app.models.constants import (
    ProjectStatus, AgentRole, ArtifactType, ArtifactStatus,
    VenueType, SourceType, QualityDimension, NDAMode,
    DiagnosticSeverity, RemediationAction, DiagnosticEventType,
    VALID_TRANSITIONS, STATUS_TO_AGENT,
)
from app.services.pipeline.orchestrator import ADVANCE_MAP, STAGE_AGENT_MAP


class TestProjectStatusTransitions:
    """Tests for VALID_TRANSITIONS completeness."""

    def test_all_statuses_in_transitions(self):
        """Every ProjectStatus except PUBLISHED should be a key in VALID_TRANSITIONS."""
        for status in ProjectStatus:
            if status == ProjectStatus.PUBLISHED:
                continue  # Terminal state, no transitions from it
            assert status in VALID_TRANSITIONS, f"{status} missing from VALID_TRANSITIONS"

    def test_all_transition_targets_are_valid_statuses(self):
        """Every value in VALID_TRANSITIONS should be a valid ProjectStatus."""
        for source, targets in VALID_TRANSITIONS.items():
            for target in targets:
                assert target in ProjectStatus.__members__.values(), \
                    f"Invalid transition target: {source} -> {target}"

    def test_no_self_transitions(self):
        """No status should transition to itself."""
        for source, targets in VALID_TRANSITIONS.items():
            assert source not in targets, f"{source} has self-transition"


class TestStatusToAgent:
    """Tests for STATUS_TO_AGENT mapping."""

    def test_all_active_statuses_have_agents(self):
        """All active (non-COMPLETE, non-terminal) statuses that need agents should be mapped."""
        active_statuses = [
            ProjectStatus.RESEARCHING, ProjectStatus.STRUCTURING,
            ProjectStatus.DRAFTING, ProjectStatus.ILLUSTRATING,
            ProjectStatus.REVIEWING, ProjectStatus.PRODUCING,
        ]
        for status in active_statuses:
            assert status in STATUS_TO_AGENT, f"{status} missing from STATUS_TO_AGENT"

    def test_agents_are_valid_roles(self):
        """All values in STATUS_TO_AGENT should be valid AgentRole values."""
        for status, agent in STATUS_TO_AGENT.items():
            assert agent in AgentRole.__members__.values(), \
                f"Invalid agent role {agent} for status {status}"


class TestAdvanceMap:
    """Tests for ADVANCE_MAP coverage."""

    def test_covers_all_complete_statuses(self):
        """ADVANCE_MAP should have an entry for every _COMPLETE status and TOPIC_SELECTED."""
        expected_keys = {
            ProjectStatus.TOPIC_SELECTED,
            ProjectStatus.RESEARCH_COMPLETE,
            ProjectStatus.STRUCTURE_COMPLETE,
            ProjectStatus.DRAFT_COMPLETE,
            ProjectStatus.ILLUSTRATION_COMPLETE,
            ProjectStatus.REVIEW_PASSED,
            ProjectStatus.PRODUCTION_COMPLETE,
        }
        for key in expected_keys:
            assert key in ADVANCE_MAP, f"{key} missing from ADVANCE_MAP"

    def test_advance_targets_are_valid(self):
        """All ADVANCE_MAP targets should be valid ProjectStatus values."""
        for source, target in ADVANCE_MAP.items():
            assert target in ProjectStatus.__members__.values(), \
                f"Invalid advance target: {source} -> {target}"

    def test_no_backward_advances(self):
        """Advance should move forward in the pipeline, not backward."""
        status_order = list(ProjectStatus)
        for source, target in ADVANCE_MAP.items():
            source_idx = status_order.index(source)
            target_idx = status_order.index(target)
            assert target_idx > source_idx, \
                f"Backward advance: {source} (idx={source_idx}) -> {target} (idx={target_idx})"


class TestArtifactType:
    """Tests for ArtifactType enum completeness."""

    def test_has_expected_values(self):
        """ArtifactType should contain all expected artifact types."""
        expected = {"research_plan", "outline", "section_draft", "figures", "review", "production_output"}
        actual = {t.value for t in ArtifactType}
        assert expected == actual, f"Mismatch: expected {expected}, got {actual}"


class TestEnumNoDuplicates:
    """Tests for enum integrity: no duplicate values."""

    def test_project_status_no_duplicates(self):
        """ProjectStatus should have no duplicate values."""
        values = [s.value for s in ProjectStatus]
        assert len(values) == len(set(values)), "Duplicate values in ProjectStatus"

    def test_agent_role_no_duplicates(self):
        """AgentRole should have no duplicate values."""
        values = [r.value for r in AgentRole]
        assert len(values) == len(set(values)), "Duplicate values in AgentRole"

    def test_artifact_type_no_duplicates(self):
        """ArtifactType should have no duplicate values."""
        values = [t.value for t in ArtifactType]
        assert len(values) == len(set(values)), "Duplicate values in ArtifactType"

    def test_artifact_status_no_duplicates(self):
        """ArtifactStatus should have no duplicate values."""
        values = [s.value for s in ArtifactStatus]
        assert len(values) == len(set(values)), "Duplicate values in ArtifactStatus"

    def test_venue_type_no_duplicates(self):
        """VenueType should have no duplicate values."""
        values = [v.value for v in VenueType]
        assert len(values) == len(set(values)), "Duplicate values in VenueType"

    def test_source_type_no_duplicates(self):
        """SourceType should have no duplicate values."""
        values = [s.value for s in SourceType]
        assert len(values) == len(set(values)), "Duplicate values in SourceType"

    def test_quality_dimension_no_duplicates(self):
        """QualityDimension should have no duplicate values."""
        values = [q.value for q in QualityDimension]
        assert len(values) == len(set(values)), "Duplicate values in QualityDimension"

    def test_nda_mode_no_duplicates(self):
        """NDAMode should have no duplicate values."""
        values = [n.value for n in NDAMode]
        assert len(values) == len(set(values)), "Duplicate values in NDAMode"

    def test_diagnostic_severity_no_duplicates(self):
        """DiagnosticSeverity should have no duplicate values."""
        values = [d.value for d in DiagnosticSeverity]
        assert len(values) == len(set(values)), "Duplicate values in DiagnosticSeverity"

    def test_remediation_action_no_duplicates(self):
        """RemediationAction should have no duplicate values."""
        values = [r.value for r in RemediationAction]
        assert len(values) == len(set(values)), "Duplicate values in RemediationAction"

    def test_diagnostic_event_type_no_duplicates(self):
        """DiagnosticEventType should have no duplicate values."""
        values = [d.value for d in DiagnosticEventType]
        assert len(values) == len(set(values)), "Duplicate values in DiagnosticEventType"


class TestEnumCompleteness:
    """Tests for cross-enum consistency."""

    def test_venue_type_has_expected_values(self):
        """VenueType should cover the four main venue categories."""
        expected = {"practitioner_repository", "academic_conference", "industry_publication", "self_published", "custom"}
        actual = {v.value for v in VenueType}
        assert expected == actual

    def test_nda_mode_has_three_modes(self):
        """NDAMode should have flag, auto_generalize, and block."""
        expected = {"flag", "auto_generalize", "block"}
        actual = {m.value for m in NDAMode}
        assert expected == actual

    def test_diagnostic_severity_has_four_levels(self):
        """DiagnosticSeverity should have low, medium, high, critical."""
        expected = {"low", "medium", "high", "critical"}
        actual = {s.value for s in DiagnosticSeverity}
        assert expected == actual
