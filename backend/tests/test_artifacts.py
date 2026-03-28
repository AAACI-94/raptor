"""Tests for artifact_service.py and artifacts router."""

import json
import uuid

from app.models.envelope import ArtifactEnvelope, ArtifactMetadata
from app.services import artifact_service


def _make_envelope(project_id: str, artifact_type: str = "research_plan",
                   source_agent: str = "research_strategist", version: int = 1) -> ArtifactEnvelope:
    """Helper to create a valid ArtifactEnvelope for testing."""
    return ArtifactEnvelope(
        artifact_id=str(uuid.uuid4()),
        artifact_type=artifact_type,
        source_agent=source_agent,
        project_id=project_id,
        version=version,
        payload={"stub": True},
        metadata=ArtifactMetadata(model="test-model", duration_ms=100),
        status="submitted",
    )


def _create_project(client) -> str:
    """Helper to create a project and return its ID."""
    resp = client.post("/api/projects", json={"title": "Artifact Test Project"})
    return resp.json()["id"]


class TestArtifactService:
    """Unit tests for artifact_service functions."""

    def test_store_artifact_returns_id(self, setup_test_db, client):
        """store_artifact should create an artifact and return its ID."""
        project_id = _create_project(client)
        envelope = _make_envelope(project_id)
        artifact_id = artifact_service.store_artifact(envelope)
        assert artifact_id is not None
        assert isinstance(artifact_id, str)
        assert len(artifact_id) > 0

    def test_get_artifact_retrieves_by_id(self, setup_test_db, client):
        """get_artifact should retrieve a stored artifact by ID."""
        project_id = _create_project(client)
        envelope = _make_envelope(project_id)
        artifact_id = artifact_service.store_artifact(envelope)

        retrieved = artifact_service.get_artifact(artifact_id)
        assert retrieved.artifact_id == artifact_id
        assert retrieved.artifact_type == "research_plan"
        assert retrieved.source_agent == "research_strategist"
        assert retrieved.project_id == project_id

    def test_get_artifact_raises_for_missing(self, setup_test_db):
        """get_artifact should raise ValueError for a nonexistent ID."""
        import pytest
        with pytest.raises(ValueError, match="Artifact not found"):
            artifact_service.get_artifact("nonexistent-id")

    def test_list_artifacts_returns_all_for_project(self, setup_test_db, client):
        """list_artifacts should return all artifacts for a project."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=1))
        artifact_service.store_artifact(_make_envelope(project_id, "outline", source_agent="structure_architect", version=1))

        results = artifact_service.list_artifacts(project_id)
        assert len(results) == 2

    def test_list_artifacts_filters_by_type(self, setup_test_db, client):
        """list_artifacts should filter by artifact_type when provided."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=1))
        artifact_service.store_artifact(_make_envelope(project_id, "outline", source_agent="structure_architect", version=1))

        results = artifact_service.list_artifacts(project_id, artifact_type="research_plan")
        assert len(results) == 1
        assert results[0]["artifact_type"] == "research_plan"

    def test_list_artifacts_filters_by_agent(self, setup_test_db, client):
        """list_artifacts should filter by source agent when provided."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", "research_strategist", version=1))
        artifact_service.store_artifact(_make_envelope(project_id, "outline", "structure_architect", version=1))

        results = artifact_service.list_artifacts(project_id, agent="structure_architect")
        assert len(results) == 1
        assert results[0]["source_agent"] == "structure_architect"

    def test_get_latest_artifact_returns_highest_version(self, setup_test_db, client):
        """get_latest_artifact should return the artifact with the highest version number."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=1))
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=2))
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=3))

        latest = artifact_service.get_latest_artifact(project_id, "research_plan")
        assert latest is not None
        assert latest.version == 3

    def test_get_latest_artifact_returns_none_when_empty(self, setup_test_db, client):
        """get_latest_artifact should return None when no artifacts exist."""
        project_id = _create_project(client)
        result = artifact_service.get_latest_artifact(project_id, "research_plan")
        assert result is None

    def test_get_next_version_increments(self, setup_test_db, client):
        """get_next_version should return 1 for first artifact, then increment."""
        project_id = _create_project(client)

        v1 = artifact_service.get_next_version(project_id, "research_plan", "research_strategist")
        assert v1 == 1

        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=1))
        v2 = artifact_service.get_next_version(project_id, "research_plan", "research_strategist")
        assert v2 == 2

    def test_get_next_version_scopes_by_agent(self, setup_test_db, client):
        """get_next_version should scope version counting to the specific agent."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", "research_strategist", version=1))

        # Different agent should start at version 1
        v = artifact_service.get_next_version(project_id, "research_plan", "other_agent")
        assert v == 1


class TestArtifactsRouter:
    """API-level tests for artifact endpoints."""

    def test_list_artifacts_endpoint(self, client):
        """GET /api/projects/{id}/artifacts should return artifact list."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "research_plan", version=1))

        resp = client.get(f"/api/projects/{project_id}/artifacts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["artifact_type"] == "research_plan"

    def test_list_artifacts_empty(self, client):
        """GET /api/projects/{id}/artifacts should return empty list for new project."""
        project_id = _create_project(client)
        resp = client.get(f"/api/projects/{project_id}/artifacts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_artifact_endpoint(self, client):
        """GET /api/artifacts/{id} should return artifact details."""
        project_id = _create_project(client)
        envelope = _make_envelope(project_id)
        artifact_id = artifact_service.store_artifact(envelope)

        resp = client.get(f"/api/artifacts/{artifact_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["artifact_id"] == artifact_id
        assert data["artifact_type"] == "research_plan"

    def test_get_artifact_404_for_missing(self, client):
        """GET /api/artifacts/{id} should return 404 for nonexistent artifact."""
        resp = client.get("/api/artifacts/nonexistent-id")
        assert resp.status_code == 404

    def test_get_latest_artifact_endpoint(self, client):
        """GET /api/projects/{id}/artifacts/latest/{type} should return latest version."""
        project_id = _create_project(client)
        artifact_service.store_artifact(_make_envelope(project_id, "outline", "structure_architect", version=1))
        artifact_service.store_artifact(_make_envelope(project_id, "outline", "structure_architect", version=2))

        resp = client.get(f"/api/projects/{project_id}/artifacts/latest/outline")
        assert resp.status_code == 200
        assert resp.json()["version"] == 2

    def test_get_latest_artifact_404_when_none(self, client):
        """GET /api/projects/{id}/artifacts/latest/{type} should return 404 when no artifacts."""
        project_id = _create_project(client)
        resp = client.get(f"/api/projects/{project_id}/artifacts/latest/outline")
        assert resp.status_code == 404
