"""Project CRUD operations."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary

logger = logging.getLogger(__name__)


def create_project(data: ProjectCreate) -> Project:
    """Create a new project."""
    db = get_db()
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    nda_json = json.dumps(data.nda_config.model_dump()) if data.nda_config else None

    db.execute(
        """INSERT INTO projects (id, title, topic_description, author_context,
           venue_profile_id, status, nda_config, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'TOPIC_SELECTED', ?, ?, ?)""",
        (project_id, data.title, data.topic_description, data.author_context,
         data.venue_profile_id, nda_json, now, now),
    )
    db.commit()
    logger.info("[project] Created project %s: %s", project_id, data.title)
    return get_project(project_id)


def get_project(project_id: str) -> Project:
    """Get a project by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ValueError(f"Project not found: {project_id}")
    return _row_to_project(row)


def list_projects() -> list[ProjectSummary]:
    """List all projects."""
    db = get_db()
    rows = db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return [
        ProjectSummary(
            id=r["id"], title=r["title"], venue_profile_id=r["venue_profile_id"],
            status=r["status"], revision_cycles=r["revision_cycles"],
            created_at=r["created_at"], updated_at=r["updated_at"],
        )
        for r in rows
    ]


def update_project(project_id: str, data: ProjectUpdate) -> Project:
    """Update a project's editable fields."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    project = get_project(project_id)
    updates: dict = {}
    if data.title is not None:
        updates["title"] = data.title
    if data.topic_description is not None:
        updates["topic_description"] = data.topic_description
    if data.author_context is not None:
        updates["author_context"] = data.author_context
    if data.venue_profile_id is not None:
        updates["venue_profile_id"] = data.venue_profile_id
    if data.nda_config is not None:
        updates["nda_config"] = json.dumps(data.nda_config.model_dump())

    if updates:
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]
        db.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        db.commit()
        logger.info("[project] Updated project %s", project_id)

    return get_project(project_id)


def delete_project(project_id: str) -> None:
    """Delete a project and all related data."""
    db = get_db()
    # Delete in dependency order
    db.execute("DELETE FROM audit_log WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM author_feedback WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM quality_scores WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM token_usage WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM decision_logs WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM research_sources WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM artifacts WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    logger.info("[project] Deleted project %s", project_id)


def update_project_status(project_id: str, status: str) -> None:
    """Update a project's pipeline status."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        (status, now, project_id),
    )
    db.commit()


def increment_revision_cycles(project_id: str) -> int:
    """Increment and return the revision cycle count."""
    db = get_db()
    db.execute(
        "UPDATE projects SET revision_cycles = revision_cycles + 1 WHERE id = ?",
        (project_id,),
    )
    db.commit()
    row = db.execute("SELECT revision_cycles FROM projects WHERE id = ?", (project_id,)).fetchone()
    return row["revision_cycles"]


def _row_to_project(row) -> Project:
    """Convert a database row to a Project model."""
    nda_config = None
    if row["nda_config"]:
        from app.models.project import NDAConfig
        nda_config = NDAConfig(**json.loads(row["nda_config"]))
    return Project(
        id=row["id"],
        title=row["title"],
        topic_description=row["topic_description"] or "",
        author_context=row["author_context"] or "",
        venue_profile_id=row["venue_profile_id"],
        status=row["status"],
        nda_config=nda_config,
        revision_cycles=row["revision_cycles"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
