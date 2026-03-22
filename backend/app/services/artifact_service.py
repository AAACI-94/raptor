"""Artifact CRUD operations. Artifacts are immutable; revisions create new versions."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.envelope import ArtifactEnvelope

logger = logging.getLogger(__name__)


def store_artifact(envelope: ArtifactEnvelope) -> str:
    """Store an artifact envelope. Returns the artifact ID."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    if not envelope.artifact_id:
        envelope.artifact_id = str(uuid.uuid4())

    envelope.created_at = now
    envelope.updated_at = now

    db.execute(
        """INSERT INTO artifacts (id, project_id, artifact_type, source_agent, target_agent,
           version, status, envelope, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (envelope.artifact_id, envelope.project_id, envelope.artifact_type,
         envelope.source_agent, envelope.target_agent, envelope.version,
         envelope.status, json.dumps(envelope.model_dump()), now),
    )
    db.commit()
    logger.info("[artifact] Stored %s from %s (v%d) for project %s",
                envelope.artifact_type, envelope.source_agent, envelope.version, envelope.project_id)
    return envelope.artifact_id


def get_artifact(artifact_id: str) -> ArtifactEnvelope:
    """Get an artifact by ID."""
    db = get_db()
    row = db.execute("SELECT envelope FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
    if row is None:
        raise ValueError(f"Artifact not found: {artifact_id}")
    return ArtifactEnvelope(**json.loads(row["envelope"]))


def list_artifacts(project_id: str, artifact_type: str | None = None, agent: str | None = None) -> list[dict]:
    """List artifacts for a project, optionally filtered."""
    db = get_db()
    query = "SELECT id, artifact_type, source_agent, version, status, created_at FROM artifacts WHERE project_id = ?"
    params: list = [project_id]

    if artifact_type:
        query += " AND artifact_type = ?"
        params.append(artifact_type)
    if agent:
        query += " AND source_agent = ?"
        params.append(agent)

    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()

    return [
        {
            "id": r["id"],
            "artifact_type": r["artifact_type"],
            "source_agent": r["source_agent"],
            "version": r["version"],
            "status": r["status"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_latest_artifact(project_id: str, artifact_type: str) -> ArtifactEnvelope | None:
    """Get the latest version of an artifact type for a project."""
    db = get_db()
    row = db.execute(
        """SELECT envelope FROM artifacts
           WHERE project_id = ? AND artifact_type = ?
           ORDER BY version DESC LIMIT 1""",
        (project_id, artifact_type),
    ).fetchone()

    if row is None:
        return None
    return ArtifactEnvelope(**json.loads(row["envelope"]))


def get_next_version(project_id: str, artifact_type: str, source_agent: str) -> int:
    """Get the next version number for an artifact."""
    db = get_db()
    row = db.execute(
        """SELECT MAX(version) as max_v FROM artifacts
           WHERE project_id = ? AND artifact_type = ? AND source_agent = ?""",
        (project_id, artifact_type, source_agent),
    ).fetchone()
    return (row["max_v"] or 0) + 1
