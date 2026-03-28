"""Tests for feedback endpoint and rubric adjustment logic."""

import json
import uuid
from datetime import datetime, timezone

from app.core.database import get_db

_artifact_version_counter = 0


def _next_artifact_version() -> int:
    global _artifact_version_counter
    _artifact_version_counter += 1
    return _artifact_version_counter


def _create_project_with_venue(client) -> tuple[str, str]:
    """Helper to create a project with a venue. Returns (project_id, venue_id)."""
    venues = client.get("/api/publications").json()
    venue_id = venues[0]["id"]
    resp = client.post("/api/projects", json={
        "title": "Feedback Test",
        "topic_description": "Testing feedback loop",
        "venue_profile_id": venue_id,
    })
    return resp.json()["id"], venue_id


def _create_artifact(project_id: str) -> str:
    """Insert a minimal artifact with a unique version and return its ID."""
    db = get_db()
    artifact_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    version = _next_artifact_version()
    db.execute(
        "INSERT INTO artifacts (id, project_id, artifact_type, source_agent, version, status, envelope, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (artifact_id, project_id, "review", "critical_reviewer", version, "submitted", "{}", now),
    )
    db.commit()
    return artifact_id


class TestFeedbackSubmission:
    """Tests for the POST /api/observatory/feedback endpoint."""

    def test_submit_feedback_stores(self, client):
        """Submit feedback should store entry and return ID with delta."""
        project_id, _ = _create_project_with_venue(client)
        artifact_id = _create_artifact(project_id)

        resp = client.post("/api/observatory/feedback", json={
            "project_id": project_id,
            "artifact_id": artifact_id,
            "dimension": "novelty",
            "author_rating": 8.0,
            "system_rating": 6.0,
            "feedback_text": "System undervalues novelty.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["dimension"] == "novelty"

    def test_delta_computed_correctly(self, client):
        """Delta should equal author_rating minus system_rating."""
        project_id, _ = _create_project_with_venue(client)
        artifact_id = _create_artifact(project_id)

        resp = client.post("/api/observatory/feedback", json={
            "project_id": project_id,
            "artifact_id": artifact_id,
            "dimension": "rigor",
            "author_rating": 9.0,
            "system_rating": 6.5,
        })
        data = resp.json()
        assert data["delta"] == 2.5

    def test_negative_delta(self, client):
        """Delta should be negative when system rates higher than author."""
        project_id, _ = _create_project_with_venue(client)
        artifact_id = _create_artifact(project_id)

        resp = client.post("/api/observatory/feedback", json={
            "project_id": project_id,
            "artifact_id": artifact_id,
            "dimension": "accessibility",
            "author_rating": 5.0,
            "system_rating": 8.0,
        })
        data = resp.json()
        assert data["delta"] == -3.0

    def test_feedback_persists_in_db(self, client):
        """Feedback should be retrievable from the database after submission."""
        project_id, _ = _create_project_with_venue(client)
        artifact_id = _create_artifact(project_id)

        client.post("/api/observatory/feedback", json={
            "project_id": project_id,
            "artifact_id": artifact_id,
            "dimension": "completeness",
            "author_rating": 7.0,
            "system_rating": 7.0,
        })

        db = get_db()
        rows = db.execute(
            "SELECT * FROM author_feedback WHERE project_id = ? AND dimension = 'completeness'", (project_id,)
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0]["delta"] == 0.0


class TestRubricAdjustment:
    """Tests for rubric adjustment trigger logic."""

    def test_no_adjustment_with_few_feedbacks(self, client):
        """Rubric should not adjust with fewer than 3 feedbacks on a unique dimension."""
        project_id, venue_id = _create_project_with_venue(client)
        # Use a unique dimension name to avoid cross-test contamination
        dim = f"test_dim_{uuid.uuid4().hex[:8]}"

        for _ in range(2):
            artifact_id = _create_artifact(project_id)
            client.post("/api/observatory/feedback", json={
                "project_id": project_id,
                "artifact_id": artifact_id,
                "dimension": dim,
                "author_rating": 9.0,
                "system_rating": 5.0,
            })

        db = get_db()
        adjustments = db.execute(
            "SELECT * FROM rubric_adjustments WHERE venue_profile_id = ? AND dimension = ?",
            (venue_id, dim)
        ).fetchall()
        assert len(adjustments) == 0

    def test_no_adjustment_for_small_delta(self, client):
        """Rubric should not adjust when average delta is within threshold (<=2.0)."""
        project_id, venue_id = _create_project_with_venue(client)
        dim = f"test_small_{uuid.uuid4().hex[:8]}"

        for _ in range(3):
            artifact_id = _create_artifact(project_id)
            client.post("/api/observatory/feedback", json={
                "project_id": project_id,
                "artifact_id": artifact_id,
                "dimension": dim,
                "author_rating": 7.0,
                "system_rating": 6.0,  # delta = 1.0, avg = 1.0 < 2.0
            })

        db = get_db()
        adjustments = db.execute(
            "SELECT * FROM rubric_adjustments WHERE venue_profile_id = ? AND dimension = ?",
            (venue_id, dim)
        ).fetchall()
        assert len(adjustments) == 0

    def test_adjustment_triggered_for_known_dimension(self, client):
        """Rubric should adjust after 3 feedbacks with large divergence on a known dimension."""
        project_id, venue_id = _create_project_with_venue(client)

        # Get baseline adjustment count for this venue
        db = get_db()
        baseline = len(db.execute(
            "SELECT * FROM rubric_adjustments WHERE venue_profile_id = ?", (venue_id,)
        ).fetchall())

        # Use 'novelty' which exists in all default venue rubrics
        for _ in range(3):
            artifact_id = _create_artifact(project_id)
            client.post("/api/observatory/feedback", json={
                "project_id": project_id,
                "artifact_id": artifact_id,
                "dimension": "novelty",
                "author_rating": 9.0,
                "system_rating": 5.0,  # delta = 4.0, avg > 2.0
            })

        adjustments = db.execute(
            "SELECT * FROM rubric_adjustments WHERE venue_profile_id = ?", (venue_id,)
        ).fetchall()
        # Should have more adjustments than baseline
        assert len(adjustments) > baseline

    def test_adjustment_creates_snapshot(self, client):
        """Rubric adjustment should create a snapshot before modifying."""
        project_id, venue_id = _create_project_with_venue(client)

        db = get_db()
        baseline_snapshots = len(db.execute(
            "SELECT * FROM rubric_snapshots WHERE venue_profile_id = ?", (venue_id,)
        ).fetchall())

        for _ in range(3):
            artifact_id = _create_artifact(project_id)
            client.post("/api/observatory/feedback", json={
                "project_id": project_id,
                "artifact_id": artifact_id,
                "dimension": "novelty",
                "author_rating": 9.0,
                "system_rating": 5.0,
            })

        snapshots = db.execute(
            "SELECT * FROM rubric_snapshots WHERE venue_profile_id = ?", (venue_id,)
        ).fetchall()
        assert len(snapshots) > baseline_snapshots
