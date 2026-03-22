"""Pydantic model and constant tests."""

from app.models.constants import (
    AgentRole, ProjectStatus, ArtifactType, VenueType, QualityDimension,
    VALID_TRANSITIONS, STATUS_TO_AGENT,
)
from app.models.envelope import ArtifactEnvelope, ArtifactMetadata, DecisionLogEntry, RejectionContext
from app.models.project import ProjectCreate, Project, NDAConfig


def test_agent_roles_complete():
    """All expected agent roles should exist."""
    roles = list(AgentRole)
    assert len(roles) == 6
    assert AgentRole.RESEARCH_STRATEGIST in roles
    assert AgentRole.CRITICAL_REVIEWER in roles
    assert AgentRole.OBSERVATORY in roles


def test_project_statuses_cover_full_pipeline():
    """Project statuses should cover the full pipeline lifecycle."""
    statuses = list(ProjectStatus)
    assert ProjectStatus.TOPIC_SELECTED in statuses
    assert ProjectStatus.RESEARCHING in statuses
    assert ProjectStatus.PUBLISHED in statuses
    assert ProjectStatus.REVISION_REQUESTED in statuses


def test_valid_transitions_complete():
    """Every non-terminal status should have valid transitions."""
    for status in ProjectStatus:
        if status != ProjectStatus.PUBLISHED:
            assert status in VALID_TRANSITIONS, f"Missing transitions for {status}"


def test_artifact_envelope_serialization():
    """Artifact envelope should serialize and deserialize correctly."""
    envelope = ArtifactEnvelope(
        artifact_id="test-123",
        artifact_type=ArtifactType.RESEARCH_PLAN,
        source_agent=AgentRole.RESEARCH_STRATEGIST,
        project_id="proj-456",
        payload={"contribution_claim": "Test claim", "sources": []},
        metadata=ArtifactMetadata(model="claude-sonnet-4-20250514", duration_ms=1000),
    )

    # Serialize
    data = envelope.model_dump()
    assert data["artifact_id"] == "test-123"
    assert data["payload"]["contribution_claim"] == "Test claim"

    # Deserialize
    restored = ArtifactEnvelope(**data)
    assert restored.artifact_id == "test-123"
    assert restored.metadata.model == "claude-sonnet-4-20250514"


def test_rejection_context():
    """Rejection context should carry structured feedback."""
    rejection = RejectionContext(
        rejecting_agent="critical_reviewer",
        failed_criteria=["evidence_quality below threshold"],
        required_changes=["Add empirical data to Section 4.2"],
        target_for_revision="domain_writer",
    )
    assert rejection.rejecting_agent == "critical_reviewer"
    assert len(rejection.failed_criteria) == 1
    assert len(rejection.required_changes) == 1


def test_nda_config():
    """NDA config should support all three modes."""
    config = NDAConfig(
        sensitivity_level="moderate",
        mode="flag",
        blocked_terms=["Acme Corp", "Project Phoenix"],
    )
    assert config.mode == "flag"
    assert len(config.blocked_terms) == 2


def test_project_create_minimal():
    """Project can be created with just a title."""
    project = ProjectCreate(title="Test Paper")
    assert project.title == "Test Paper"
    assert project.topic_description == ""
