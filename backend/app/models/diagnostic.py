"""Diagnostic and remediation models for the self-healing system."""

from pydantic import BaseModel, Field
from typing import Any


class Diagnosis(BaseModel):
    """Structured root cause analysis from the Diagnostic Agent."""
    correlation_id: str
    error_class: str
    root_cause: str
    classification: str  # "transient", "structural", "environmental", "quality"
    severity: str  # DiagnosticSeverity value
    recommended_actions: list[str] = Field(default_factory=list)  # RemediationAction values
    context_notes: str = ""
    confidence: float = 0.0


class RemediationResult(BaseModel):
    """Outcome of a remediation attempt."""
    success: bool
    action_taken: str  # RemediationAction value
    attempt_number: int
    envelope: dict[str, Any] | None = None  # The fixed artifact envelope, if successful
    notes: str = ""
    duration_ms: int = 0


class DiagnosticEvent(BaseModel):
    """A diagnostic event record for storage and display."""
    id: str
    project_id: str
    correlation_id: str
    event_type: str  # DiagnosticEventType value
    severity: str  # DiagnosticSeverity value
    agent_role: str
    pipeline_stage: str = ""
    error_class: str = ""
    error_message: str = ""
    diagnosis: dict[str, Any] | None = None
    remediation_action: str = ""
    remediation_attempt: int = 0
    remediation_success: bool | None = None
    context_snapshot: dict[str, Any] | None = None
    duration_ms: int = 0
    timestamp: str = ""
