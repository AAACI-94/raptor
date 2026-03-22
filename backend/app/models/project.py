"""Project domain models."""

from pydantic import BaseModel, Field
from typing import Any


class NDAConfig(BaseModel):
    """NDA filter configuration per project."""
    sensitivity_level: str = "moderate"  # low, moderate, high
    mode: str = "flag"  # flag, auto_generalize, block
    blocked_terms: list[str] = Field(default_factory=list)
    generalization_rules: list[dict[str, str]] = Field(default_factory=list)
    approved_generalizations: list[str] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    """Input for creating a new project."""
    title: str
    topic_description: str = ""
    author_context: str = ""
    venue_profile_id: str | None = None
    nda_config: NDAConfig | None = None


class ProjectUpdate(BaseModel):
    """Input for updating a project."""
    title: str | None = None
    topic_description: str | None = None
    author_context: str | None = None
    venue_profile_id: str | None = None
    nda_config: NDAConfig | None = None


class Project(BaseModel):
    """Full project representation."""
    id: str
    title: str
    topic_description: str = ""
    author_context: str = ""
    venue_profile_id: str | None = None
    status: str = "TOPIC_SELECTED"
    nda_config: NDAConfig | None = None
    revision_cycles: int = 0
    created_at: str = ""
    updated_at: str = ""


class ProjectSummary(BaseModel):
    """Condensed project for list views."""
    id: str
    title: str
    venue_profile_id: str | None = None
    status: str
    revision_cycles: int = 0
    created_at: str
    updated_at: str
