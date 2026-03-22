"""Agent 6: Observatory (Meta-Agent).

Traces all decisions across agents. Computes quality metrics. Tracks cost/tokens.
Manages the continuous improvement feedback loop.
"""

import json
import logging
import uuid
from typing import Any

from app.core.database import get_db
from app.models.constants import AgentRole

logger = logging.getLogger(__name__)


class Observatory:
    """The observability layer. Primarily deterministic computation over structured data."""

    role = AgentRole.OBSERVATORY

    def get_trace_summary(self, project_id: str) -> dict:
        """Get all decision logs for a project, grouped by agent."""
        db = get_db()
        rows = db.execute(
            """SELECT agent, decision, rationale, confidence, timestamp
               FROM decision_logs WHERE project_id = ?
               ORDER BY timestamp""",
            (project_id,),
        ).fetchall()

        traces: dict[str, list] = {}
        for r in rows:
            agent = r["agent"]
            if agent not in traces:
                traces[agent] = []
            traces[agent].append({
                "decision": r["decision"],
                "rationale": r["rationale"],
                "confidence": r["confidence"],
                "timestamp": r["timestamp"],
            })

        return {"project_id": project_id, "traces": traces, "total_decisions": len(rows)}

    def get_quality_metrics(self, project_id: str) -> dict:
        """Get quality scores for a project, aggregated by dimension."""
        db = get_db()
        rows = db.execute(
            """SELECT dimension, AVG(score) as avg_score, MIN(score) as min_score,
                      MAX(score) as max_score, COUNT(*) as count
               FROM quality_scores WHERE project_id = ?
               GROUP BY dimension""",
            (project_id,),
        ).fetchall()

        dimensions = {}
        for r in rows:
            dimensions[r["dimension"]] = {
                "avg_score": round(r["avg_score"], 2),
                "min_score": r["min_score"],
                "max_score": r["max_score"],
                "evaluations": r["count"],
            }

        return {"project_id": project_id, "dimensions": dimensions}

    def get_quality_trends(self, venue_id: str | None = None) -> list[dict]:
        """Get quality score trends across projects."""
        db = get_db()
        query = """SELECT p.id as project_id, p.title, p.venue_profile_id,
                          qs.dimension, AVG(qs.score) as avg_score, qs.timestamp
                   FROM quality_scores qs
                   JOIN projects p ON qs.project_id = p.id"""
        params: list = []

        if venue_id:
            query += " WHERE p.venue_profile_id = ?"
            params.append(venue_id)

        query += " GROUP BY qs.project_id, qs.dimension ORDER BY qs.timestamp"
        rows = db.execute(query, params).fetchall()

        return [
            {
                "project_id": r["project_id"],
                "title": r["title"],
                "venue": r["venue_profile_id"],
                "dimension": r["dimension"],
                "avg_score": round(r["avg_score"], 2),
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]

    def get_cost_summary(self, project_id: str | None = None) -> dict:
        """Get token usage and cost breakdown."""
        db = get_db()

        if project_id:
            rows = db.execute(
                """SELECT agent, model, SUM(input_tokens) as total_in,
                          SUM(output_tokens) as total_out, SUM(estimated_cost_usd) as total_cost,
                          COUNT(*) as calls
                   FROM token_usage WHERE project_id = ?
                   GROUP BY agent, model""",
                (project_id,),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT agent, model, SUM(input_tokens) as total_in,
                          SUM(output_tokens) as total_out, SUM(estimated_cost_usd) as total_cost,
                          COUNT(*) as calls
                   FROM token_usage GROUP BY agent, model""",
            ).fetchall()

        breakdown = []
        total_cost = 0.0
        total_in = 0
        total_out = 0

        for r in rows:
            cost = r["total_cost"]
            total_cost += cost
            total_in += r["total_in"]
            total_out += r["total_out"]
            breakdown.append({
                "agent": r["agent"],
                "model": r["model"],
                "input_tokens": r["total_in"],
                "output_tokens": r["total_out"],
                "cost_usd": round(cost, 4),
                "calls": r["calls"],
            })

        return {
            "project_id": project_id,
            "breakdown": breakdown,
            "totals": {
                "input_tokens": total_in,
                "output_tokens": total_out,
                "cost_usd": round(total_cost, 4),
            },
        }

    def get_improvement_insights(self, venue_id: str | None = None) -> list[dict]:
        """Generate improvement insights from feedback patterns."""
        db = get_db()

        # Find dimensions with consistent author-system score divergence
        query = """SELECT dimension, AVG(delta) as avg_delta,
                          COUNT(*) as feedback_count,
                          AVG(author_rating) as avg_author, AVG(system_rating) as avg_system
                   FROM author_feedback"""
        params: list = []

        if venue_id:
            query += """ JOIN artifacts a ON author_feedback.artifact_id = a.id
                        JOIN projects p ON a.project_id = p.id
                        WHERE p.venue_profile_id = ?"""
            params.append(venue_id)

        query += " GROUP BY dimension HAVING COUNT(*) >= 2"
        rows = db.execute(query, params).fetchall()

        insights = []
        for r in rows:
            avg_delta = r["avg_delta"]
            if abs(avg_delta) > 1.0:
                direction = "under-values" if avg_delta < 0 else "over-values"
                insights.append({
                    "dimension": r["dimension"],
                    "insight": f"System consistently {direction} {r['dimension']} "
                              f"(avg delta: {avg_delta:.1f} across {r['feedback_count']} ratings)",
                    "recommendation": f"{'Increase' if avg_delta < 0 else 'Decrease'} rubric weight for {r['dimension']}",
                    "avg_author_rating": round(r["avg_author"], 1),
                    "avg_system_rating": round(r["avg_system"], 1),
                    "feedback_count": r["feedback_count"],
                })

        return insights

    def get_rubric_history(self, venue_id: str) -> list[dict]:
        """Get rubric adjustment history for a venue."""
        db = get_db()
        rows = db.execute(
            """SELECT dimension, old_weight, new_weight, trigger_type, rationale, timestamp
               FROM rubric_adjustments WHERE venue_profile_id = ?
               ORDER BY timestamp DESC""",
            (venue_id,),
        ).fetchall()

        return [
            {
                "dimension": r["dimension"],
                "old_weight": r["old_weight"],
                "new_weight": r["new_weight"],
                "trigger": r["trigger_type"],
                "rationale": r["rationale"],
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]


# Singleton
observatory = Observatory()
