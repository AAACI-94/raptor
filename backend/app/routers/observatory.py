"""Observatory endpoints for traces, quality, cost, and improvement insights."""

import logging

from fastapi import APIRouter, Query

from app.agents.observatory import observatory

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/traces/{project_id}")
def get_traces(project_id: str) -> dict:
    """Get decision trace summary for a project."""
    return observatory.get_trace_summary(project_id)


@router.get("/quality/{project_id}")
def get_quality(project_id: str) -> dict:
    """Get quality metrics for a project."""
    return observatory.get_quality_metrics(project_id)


@router.get("/quality/trends")
def get_quality_trends(venue_id: str | None = Query(None)) -> dict:
    """Get quality score trends across projects."""
    return observatory.get_quality_trends(venue_id)


@router.get("/cost")
def get_cost_summary(project_id: str | None = Query(None)) -> dict:
    """Get cost breakdown."""
    return observatory.get_cost_summary(project_id)


@router.get("/cost/{project_id}")
def get_project_cost(project_id: str) -> dict:
    """Get cost breakdown for a specific project."""
    return observatory.get_cost_summary(project_id)


@router.get("/insights")
def get_insights(venue_id: str | None = Query(None)) -> dict:
    """Get improvement insights from feedback patterns."""
    return observatory.get_improvement_insights(venue_id)


@router.get("/rubric-history/{venue_id}")
def get_rubric_history(venue_id: str) -> dict:
    """Get rubric adjustment history for a venue."""
    return observatory.get_rubric_history(venue_id)


@router.get("/diagnostics/{project_id}")
def get_diagnostics(project_id: str) -> dict:
    """Get diagnostic events for a project."""
    return observatory.get_diagnostic_events(project_id)


@router.get("/healing-stats")
def get_healing_stats() -> dict:
    """Get aggregate self-healing statistics."""
    return observatory.get_healing_stats()
