"""Pipeline status and transition models."""

from pydantic import BaseModel, Field
from typing import Any


class StageTransition(BaseModel):
    """Records a pipeline stage transition."""
    from_status: str
    to_status: str
    agent: str | None = None
    reason: str = ""
    timestamp: str = ""


class PipelineStatus(BaseModel):
    """Current pipeline state for a project."""
    project_id: str
    status: str
    revision_cycles: int = 0
    max_revision_cycles: int = 3
    current_agent: str | None = None
    transitions: list[StageTransition] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class PipelineStartRequest(BaseModel):
    """Request to start or advance the pipeline."""
    pass


class PipelineRejectRequest(BaseModel):
    """Request to reject current stage output."""
    feedback: str
    target_stage: str | None = None  # Which stage to send back to


class PipelineOverrideRequest(BaseModel):
    """Request to override rejection and force-advance."""
    reason: str = ""
