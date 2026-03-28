"""Project CRUD and Library endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.project import ProjectCreate, ProjectUpdate, TagsUpdate, CategoryUpdate
from app.services import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
def create_project(data: ProjectCreate) -> dict:
    """Create a new authoring project."""
    project = project_service.create_project(data)
    return project.model_dump()


@router.get("")
def list_projects() -> list:
    """List all projects."""
    projects = project_service.list_projects()
    return [p.model_dump() for p in projects]


@router.get("/{project_id}")
def get_project(project_id: str) -> dict:
    """Get a project by ID."""
    try:
        project = project_service.get_project(project_id)
        return project.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{project_id}")
def update_project(project_id: str, data: ProjectUpdate) -> dict:
    """Update a project."""
    try:
        project = project_service.update_project(project_id, data)
        return project.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict:
    """Delete a project and all related data."""
    try:
        project_service.delete_project(project_id)
        return {"status": "deleted", "id": project_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---- Library Endpoints ----

@router.get("/library/search")
def library_search(
    q: Optional[str] = Query(None),
    venue: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    starred: Optional[bool] = Query(None),
    sort: str = Query("date"),
    order: str = Query("desc"),
) -> list:
    """Search and filter the research library."""
    tag_list = tags.split(",") if tags else None
    results = project_service.library_query(
        q=q, venue=venue, category=category, tags=tag_list,
        status=status, starred=starred, sort=sort, order=order,
    )
    return [r.model_dump() for r in results]


@router.get("/library/tags")
def library_tags() -> list:
    """Get all tags with usage counts."""
    return project_service.get_library_tags()


@router.get("/library/stats")
def library_stats() -> dict:
    """Get aggregate library statistics."""
    return project_service.get_library_stats()


@router.put("/{project_id}/tags")
def update_tags(project_id: str, data: TagsUpdate) -> dict:
    """Update a project's tags."""
    try:
        project_service.update_tags(project_id, data.tags)
        return {"id": project_id, "tags": data.tags}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{project_id}/star")
def toggle_star(project_id: str) -> dict:
    """Toggle a project's starred status."""
    try:
        new_state = project_service.toggle_star(project_id)
        return {"id": project_id, "starred": new_state}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{project_id}/category")
def update_category(project_id: str, data: CategoryUpdate) -> dict:
    """Set a project's category."""
    try:
        project_service.update_category(project_id, data.category)
        return {"id": project_id, "category": data.category}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
