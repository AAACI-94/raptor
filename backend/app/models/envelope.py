"""Artifact Envelope Protocol: the structured contract between all agents."""

from pydantic import BaseModel, Field
from typing import Any


class ArtifactMetadata(BaseModel):
    """Token usage, cost, and model information for an agent operation."""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    duration_ms: int = 0
    estimated_cost_usd: float = 0.0
    trace_id: str | None = None


class DecisionLogEntry(BaseModel):
    """A single decision made by an agent with rationale."""
    timestamp: str
    decision: str
    rationale: str
    alternatives_considered: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class QualityScoreEntry(BaseModel):
    """A quality score for a single dimension."""
    dimension: str
    score: float
    feedback: str = ""
    min_passing: float = 5.0


class ReflectionResult(BaseModel):
    """Self-reflection checkpoint result."""
    passed: bool
    issues_found: list[str] = Field(default_factory=list)
    reflection_model: str = ""
    reflection_tokens: int = 0


class RejectionContext(BaseModel):
    """Structured rejection feedback when an agent rejects upstream work."""
    rejecting_agent: str
    failed_criteria: list[str]
    required_changes: list[str]
    target_for_revision: str


class ArtifactEnvelope(BaseModel):
    """The inter-agent communication unit. Every handoff uses this structure.

    Artifacts are immutable: revisions create new versions, originals are preserved.
    """
    artifact_id: str
    artifact_type: str
    source_agent: str
    target_agent: str | None = None
    project_id: str
    version: int = 1

    # Venue context
    venue_context: dict[str, Any] = Field(default_factory=dict)

    # The actual content (agent-specific structure)
    payload: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    metadata: ArtifactMetadata
    decision_log: list[DecisionLogEntry] = Field(default_factory=list)
    quality_scores: dict[str, float] = Field(default_factory=dict)
    reflection_result: ReflectionResult | None = None

    # Status
    status: str = "draft"
    rejection_context: RejectionContext | None = None

    # Timestamps
    created_at: str = ""
    updated_at: str = ""
