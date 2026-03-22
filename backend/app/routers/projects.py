"""Project CRUD endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.models.project import ProjectCreate, ProjectUpdate
from app.services import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
def create_project(data: ProjectCreate):
    """Create a new authoring project."""
    project = project_service.create_project(data)
    return project.model_dump()


@router.get("")
def list_projects():
    """List all projects."""
    projects = project_service.list_projects()
    return [p.model_dump() for p in projects]


@router.get("/{project_id}")
def get_project(project_id: str):
    """Get a project by ID."""
    try:
        project = project_service.get_project(project_id)
        return project.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{project_id}")
def update_project(project_id: str, data: ProjectUpdate):
    """Update a project."""
    try:
        project = project_service.update_project(project_id, data)
        return project.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str):
    """Delete a project and all related data."""
    try:
        project_service.delete_project(project_id)
        return {"status": "deleted", "id": project_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
