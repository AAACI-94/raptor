"""Project CRUD operations."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_db, safe_update
from app.models.constants import ProjectStatus
from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectSummary

logger = logging.getLogger(__name__)


def create_project(data: ProjectCreate) -> Project:
    """Create a new project."""
    db = get_db()
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    nda_json = json.dumps(data.nda_config.model_dump()) if data.nda_config else None

    tags_json = json.dumps(data.tags) if data.tags else None

    db.execute(
        """INSERT INTO projects (id, title, topic_description, author_context,
           venue_profile_id, status, nda_config, tags, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, data.title, data.topic_description, data.author_context,
         data.venue_profile_id, ProjectStatus.TOPIC_SELECTED, nda_json, tags_json, data.category, now, now),
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
        _PROJECT_UPDATE_COLUMNS = {"title", "topic_description", "author_context", "venue_profile_id", "nda_config", "updated_at"}
        safe_update("projects", updates, "id", project_id, _PROJECT_UPDATE_COLUMNS)
        logger.info("[project] Updated project %s", project_id)

    return get_project(project_id)


def delete_project(project_id: str) -> None:
    """Delete a project and all related data."""
    db = get_db()
    # Delete in dependency order
    db.execute("DELETE FROM diagnostic_events WHERE project_id = ?", (project_id,))
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


def update_tags(project_id: str, tags: list[str]) -> None:
    """Update a project's tags."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE projects SET tags = ?, updated_at = ? WHERE id = ?",
        (json.dumps(tags), now, project_id),
    )
    db.commit()
    logger.info("[project] Updated tags for %s: %s", project_id, tags)


def toggle_star(project_id: str) -> bool:
    """Toggle a project's starred status. Returns new state."""
    db = get_db()
    row = db.execute("SELECT starred FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise ValueError(f"Project not found: {project_id}")
    new_state = not bool(row["starred"])
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE projects SET starred = ?, updated_at = ? WHERE id = ?",
        (new_state, now, project_id),
    )
    db.commit()
    return new_state


def update_category(project_id: str, category: str) -> None:
    """Set a project's category."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE projects SET category = ?, updated_at = ? WHERE id = ?",
        (category, now, project_id),
    )
    db.commit()


def update_library_metadata(project_id: str, **kwargs) -> None:
    """Update computed library metadata (abstract, word_count, figure_count, quality_score, total_cost)."""
    now = datetime.now(timezone.utc).isoformat()
    _LIBRARY_META_COLUMNS = {"abstract", "word_count", "figure_count", "quality_score", "total_cost_usd", "updated_at"}
    updates = {k: v for k, v in kwargs.items() if k in _LIBRARY_META_COLUMNS and v is not None}
    if updates:
        updates["updated_at"] = now
        safe_update("projects", updates, "id", project_id, _LIBRARY_META_COLUMNS)


def auto_tag_from_research(project_id: str, research_payload: dict) -> list[str]:
    """Extract tags from Research Strategist output and store them.

    Tags are derived from:
    1. Contribution claim keywords
    2. Source types present
    3. Venue type
    """
    tags = set()

    # From contribution claim
    claim = research_payload.get("contribution_claim", "")
    if claim:
        # Extract significant words (simple keyword extraction)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "shall", "can", "this", "that", "these",
                      "those", "for", "and", "but", "or", "not", "with", "from", "to", "in",
                      "on", "at", "by", "of", "as", "it", "its", "we", "our", "their"}
        words = claim.lower().split()
        keywords = [w.strip(".,;:!?()\"'") for w in words if len(w) > 3 and w.lower() not in stop_words]
        # Take top 5 most significant-looking words
        for kw in keywords[:8]:
            if kw.isalpha():
                tags.add(kw)

    # From source types
    sources = research_payload.get("sources", [])
    source_types = set(s.get("source_type", "") for s in sources if s.get("source_type"))
    for st in source_types:
        tags.add(st.replace("_", "-"))

    # Get venue info
    project = get_project(project_id)
    if project.venue_profile_id:
        tags.add(project.venue_profile_id.replace("_", "-"))

    # Merge with existing tags
    existing = project.tags or []
    merged = list(set(existing) | tags)

    update_tags(project_id, merged)
    logger.info("[project] Auto-tagged %s with %d tags", project_id, len(merged))
    return merged


def auto_extract_abstract(project_id: str, production_payload: dict) -> str:
    """Extract abstract from production output."""
    doc = production_payload.get("document", {})

    # Try explicit abstract field
    abstract = doc.get("abstract", "")
    if abstract and len(abstract.split()) >= 20:
        abstract = abstract[:800]  # Cap at ~150 words
    else:
        # Fall back to first section content
        sections = doc.get("sections", [])
        for s in sections:
            heading = s.get("heading", "").lower()
            if "abstract" in heading or "executive summary" in heading or "introduction" in heading:
                content = s.get("content", "")
                # Take first ~150 words
                words = content.split()[:150]
                abstract = " ".join(words)
                if len(words) == 150:
                    abstract += "..."
                break

    if abstract:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE projects SET abstract = ?, updated_at = ? WHERE id = ?",
            (abstract, now, project_id),
        )
        db.commit()

    return abstract


def library_query(
    q: str | None = None,
    venue: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    starred: bool | None = None,
    sort: str = "date",
    order: str = "desc",
) -> list[ProjectSummary]:
    """Query projects with filtering and search for the library view."""
    db = get_db()

    query = "SELECT * FROM projects WHERE 1=1"
    params: list = []

    if q:
        query += " AND (title LIKE ? OR topic_description LIKE ? OR tags LIKE ? OR abstract LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like])

    if venue:
        query += " AND venue_profile_id = ?"
        params.append(venue)

    if category:
        query += " AND category = ?"
        params.append(category)

    if tags:
        # OR logic: match any of the provided tags
        tag_clauses = []
        for tag in tags:
            tag_clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")
        query += f" AND ({' OR '.join(tag_clauses)})"

    if status:
        query += " AND status = ?"
        params.append(status)

    if starred is not None:
        query += " AND starred = ?"
        params.append(starred)

    # Sort
    sort_map = {
        "date": "updated_at",
        "title": "title",
        "quality": "quality_score",
        "cost": "total_cost_usd",
        "words": "word_count",
    }
    sort_col = sort_map.get(sort, "updated_at")
    order_dir = "ASC" if order == "asc" else "DESC"
    # Handle NULL quality_score in sorting
    if sort_col == "quality_score":
        query += f" ORDER BY COALESCE({sort_col}, 0) {order_dir}"
    else:
        query += f" ORDER BY {sort_col} {order_dir}"

    rows = db.execute(query, params).fetchall()
    return [_row_to_summary(r) for r in rows]


def get_library_tags() -> list[dict]:
    """Get all tags with usage counts."""
    db = get_db()
    rows = db.execute("SELECT tags FROM projects WHERE tags IS NOT NULL AND tags != '[]'").fetchall()

    tag_counts: dict[str, int] = {}
    for row in rows:
        try:
            tags = json.loads(row["tags"])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    return sorted(
        [{"tag": tag, "count": count} for tag, count in tag_counts.items()],
        key=lambda x: -x["count"],
    )


def get_library_stats() -> dict:
    """Get aggregate library statistics."""
    from app.models.project import LibraryStats
    db = get_db()

    total = db.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]

    # By venue
    venue_rows = db.execute(
        "SELECT venue_profile_id, COUNT(*) as cnt FROM projects WHERE venue_profile_id IS NOT NULL GROUP BY venue_profile_id"
    ).fetchall()
    by_venue = {r["venue_profile_id"]: r["cnt"] for r in venue_rows}

    # By category
    cat_rows = db.execute(
        "SELECT category, COUNT(*) as cnt FROM projects WHERE category IS NOT NULL GROUP BY category"
    ).fetchall()
    by_category = {r["category"]: r["cnt"] for r in cat_rows}

    # By status group
    status_groups = {"in_progress": 0, "ready_to_publish": 0, "published": 0}
    for row in db.execute("SELECT status FROM projects").fetchall():
        s = row["status"]
        if s == "PUBLISHED":
            status_groups["published"] += 1
        elif s in ("PRODUCTION_COMPLETE", "REVIEW_PASSED"):
            status_groups["ready_to_publish"] += 1
        else:
            status_groups["in_progress"] += 1

    # Aggregates
    agg = db.execute(
        "SELECT AVG(quality_score) as avg_q, SUM(total_cost_usd) as total_c, "
        "SUM(word_count) as total_w, SUM(figure_count) as total_f FROM projects"
    ).fetchone()

    return LibraryStats(
        total_projects=total,
        by_venue=by_venue,
        by_category=by_category,
        by_status_group=status_groups,
        avg_quality=round(agg["avg_q"] or 0, 1),
        total_cost=round(agg["total_c"] or 0, 2),
        total_words=agg["total_w"] or 0,
        total_figures=agg["total_f"] or 0,
        top_tags=get_library_tags()[:10],
    ).model_dump()


def _row_to_project(row) -> Project:
    """Convert a database row to a Project model."""
    nda_config = None
    if row["nda_config"]:
        from app.models.project import NDAConfig
        nda_config = NDAConfig(**json.loads(row["nda_config"]))

    tags = []
    if row["tags"]:
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            pass

    return Project(
        id=row["id"],
        title=row["title"],
        topic_description=row["topic_description"] or "",
        author_context=row["author_context"] or "",
        venue_profile_id=row["venue_profile_id"],
        status=row["status"],
        nda_config=nda_config,
        revision_cycles=row["revision_cycles"],
        tags=tags,
        category=row["category"],
        starred=bool(row["starred"]),
        abstract=row["abstract"] or "",
        word_count=row["word_count"] or 0,
        figure_count=row["figure_count"] or 0,
        quality_score=row["quality_score"],
        total_cost_usd=row["total_cost_usd"] or 0.0,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_summary(row) -> ProjectSummary:
    """Convert a database row to a ProjectSummary model."""
    tags = []
    if row["tags"]:
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            pass

    return ProjectSummary(
        id=row["id"],
        title=row["title"],
        venue_profile_id=row["venue_profile_id"],
        status=row["status"],
        revision_cycles=row["revision_cycles"],
        tags=tags,
        category=row["category"],
        starred=bool(row["starred"]),
        abstract=row["abstract"] or "",
        word_count=row["word_count"] or 0,
        figure_count=row["figure_count"] or 0,
        quality_score=row["quality_score"],
        total_cost_usd=row["total_cost_usd"] or 0.0,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
