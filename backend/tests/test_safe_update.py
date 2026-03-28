"""Tests for the safe_update database helper."""

from app.core.database import get_db, safe_update


def _create_test_project() -> str:
    """Insert a minimal project directly into DB and return its ID."""
    import uuid
    from datetime import datetime, timezone
    db = get_db()
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO projects (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (project_id, "Safe Update Test", "TOPIC_SELECTED", now, now),
    )
    db.commit()
    return project_id


class TestSafeUpdate:
    """Tests for the safe_update helper function."""

    def test_valid_columns_applied(self, setup_test_db):
        """safe_update should apply updates for columns in the allowlist."""
        project_id = _create_test_project()
        allowed = {"title", "topic_description", "updated_at"}
        safe_update("projects", {"title": "Updated Title"}, "id", project_id, allowed)

        db = get_db()
        row = db.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
        assert row["title"] == "Updated Title"

    def test_filters_non_allowlisted_columns(self, setup_test_db):
        """safe_update should silently ignore columns not in the allowlist."""
        project_id = _create_test_project()
        allowed = {"title", "updated_at"}
        # Attempt to update both an allowed and a non-allowed column
        safe_update("projects", {"title": "Allowed", "status": "HACKED"}, "id", project_id, allowed)

        db = get_db()
        row = db.execute("SELECT title, status FROM projects WHERE id = ?", (project_id,)).fetchone()
        assert row["title"] == "Allowed"
        assert row["status"] == "TOPIC_SELECTED"  # Not changed

    def test_empty_updates_is_noop(self, setup_test_db):
        """safe_update with empty updates dict should be a no-op."""
        project_id = _create_test_project()
        allowed = {"title", "updated_at"}
        # Should not raise or modify anything
        safe_update("projects", {}, "id", project_id, allowed)

        db = get_db()
        row = db.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
        assert row["title"] == "Safe Update Test"  # Unchanged

    def test_all_non_allowed_is_noop(self, setup_test_db):
        """safe_update where all columns are filtered out should be a no-op."""
        project_id = _create_test_project()
        allowed = {"title"}
        safe_update("projects", {"status": "HACKED", "nda_config": "bad"}, "id", project_id, allowed)

        db = get_db()
        row = db.execute("SELECT title, status FROM projects WHERE id = ?", (project_id,)).fetchone()
        assert row["title"] == "Safe Update Test"
        assert row["status"] == "TOPIC_SELECTED"

    def test_multiple_columns_update(self, setup_test_db):
        """safe_update should handle multiple valid columns at once."""
        project_id = _create_test_project()
        allowed = {"title", "topic_description", "author_context", "updated_at"}
        safe_update(
            "projects",
            {"title": "New Title", "topic_description": "New Topic", "author_context": "New Context"},
            "id", project_id, allowed,
        )

        db = get_db()
        row = db.execute(
            "SELECT title, topic_description, author_context FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        assert row["title"] == "New Title"
        assert row["topic_description"] == "New Topic"
        assert row["author_context"] == "New Context"

    def test_update_nonexistent_row(self, setup_test_db):
        """safe_update on a non-matching where clause should not raise."""
        allowed = {"title"}
        # Should not raise; just matches zero rows
        safe_update("projects", {"title": "Ghost"}, "id", "nonexistent-id", allowed)
