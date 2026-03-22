"""Author feedback endpoints for the continuous improvement loop."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackSubmission(BaseModel):
    """Author feedback on a review dimension."""
    project_id: str
    artifact_id: str
    dimension: str
    author_rating: float
    system_rating: float
    feedback_text: str = ""


class RubricAdjustmentRequest(BaseModel):
    """Request to apply computed rubric adjustments."""
    venue_id: str


@router.post("/feedback")
def submit_feedback(data: FeedbackSubmission):
    """Submit author feedback for a review dimension."""
    db = get_db()
    delta = data.author_rating - data.system_rating
    now = datetime.now(timezone.utc).isoformat()

    feedback_id = str(uuid.uuid4())
    db.execute(
        """INSERT INTO author_feedback (id, project_id, artifact_id, dimension,
           author_rating, system_rating, delta, feedback_text, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (feedback_id, data.project_id, data.artifact_id, data.dimension,
         data.author_rating, data.system_rating, delta, data.feedback_text, now),
    )
    db.commit()

    logger.info("[feedback] Recorded: %s dimension=%s author=%.1f system=%.1f delta=%.1f",
                data.project_id, data.dimension, data.author_rating, data.system_rating, delta)

    # Check if rubric adjustment is triggered
    _check_rubric_adjustment(data.dimension)

    return {"id": feedback_id, "delta": delta, "dimension": data.dimension}


def _check_rubric_adjustment(dimension: str) -> None:
    """Check if a rubric adjustment should be triggered based on feedback patterns.

    Algorithm (v1): If author ratings consistently diverge from system ratings
    on a dimension (>2 point delta across 3+ ratings), adjust the weight.
    """
    db = get_db()
    rows = db.execute(
        """SELECT af.delta, p.venue_profile_id
           FROM author_feedback af
           JOIN artifacts a ON af.artifact_id = a.id
           JOIN projects p ON af.project_id = p.id
           WHERE af.dimension = ?
           ORDER BY af.timestamp DESC LIMIT 5""",
        (dimension,),
    ).fetchall()

    if len(rows) < 3:
        return

    # Check for consistent divergence
    deltas = [r["delta"] for r in rows[:3]]
    avg_delta = sum(deltas) / len(deltas)
    venue_id = rows[0]["venue_profile_id"]

    if abs(avg_delta) <= 2.0 or not venue_id:
        return

    # Trigger adjustment
    logger.info("[feedback] Rubric adjustment triggered for %s: avg_delta=%.1f", dimension, avg_delta)

    # Get current rubric
    venue_row = db.execute("SELECT profile_data FROM venue_profiles WHERE id = ?", (venue_id,)).fetchone()
    if not venue_row:
        return

    profile_data = json.loads(venue_row["profile_data"])
    rubric = profile_data.get("quality_rubric", {})
    dimensions = rubric.get("dimensions", [])

    # Find the dimension and adjust
    for dim in dimensions:
        if dim["name"] == dimension:
            old_weight = dim["weight"]
            # Adjust by +/- 0.05, capped
            adjustment = 0.05 if avg_delta < 0 else -0.05  # Under-valuing = increase weight
            new_weight = max(0.05, min(0.50, old_weight + adjustment))

            # Snapshot current rubric
            db.execute(
                """INSERT INTO rubric_snapshots (id, venue_profile_id, rubric_data, snapshot_reason)
                   VALUES (?, ?, ?, ?)""",
                (str(uuid.uuid4()), venue_id, json.dumps(rubric), f"Before auto-adjustment of {dimension}"),
            )

            # Apply adjustment
            dim["weight"] = new_weight

            # Normalize weights to sum to 1.0
            total = sum(d["weight"] for d in dimensions)
            for d in dimensions:
                d["weight"] = round(d["weight"] / total, 4)

            # Save updated rubric
            profile_data["quality_rubric"]["dimensions"] = dimensions
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "UPDATE venue_profiles SET profile_data = ?, updated_at = ? WHERE id = ?",
                (json.dumps(profile_data), now, venue_id),
            )

            # Log the adjustment
            db.execute(
                """INSERT INTO rubric_adjustments (id, venue_profile_id, dimension,
                   old_weight, new_weight, trigger_type, rationale)
                   VALUES (?, ?, ?, ?, ?, 'author_rating', ?)""",
                (str(uuid.uuid4()), venue_id, dimension, old_weight, new_weight,
                 f"avg_delta={avg_delta:.1f} across 3 ratings"),
            )

            db.commit()
            logger.info("[feedback] Adjusted %s weight: %.3f -> %.3f for venue %s",
                       dimension, old_weight, new_weight, venue_id)
            break
