"""Artifact endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.services import artifact_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/artifacts")
def list_artifacts(
    project_id: str,
    artifact_type: str | None = Query(None),
    agent: str | None = Query(None),
) -> list:
    """List artifacts for a project."""
    return artifact_service.list_artifacts(project_id, artifact_type, agent)


@router.get("/projects/{project_id}/artifacts/latest/{artifact_type}")
def get_latest_artifact(project_id: str, artifact_type: str) -> dict:
    """Get the latest artifact of a given type."""
    artifact = artifact_service.get_latest_artifact(project_id, artifact_type)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"No {artifact_type} artifact found")
    return artifact.model_dump()


@router.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: str) -> dict:
    """Get a specific artifact by ID."""
    try:
        artifact = artifact_service.get_artifact(artifact_id)
        return artifact.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
