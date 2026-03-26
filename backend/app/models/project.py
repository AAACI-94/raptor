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
    tags: list[str] = Field(default_factory=list)
    category: str | None = None


class ProjectUpdate(BaseModel):
    """Input for updating a project."""
    title: str | None = None
    topic_description: str | None = None
    author_context: str | None = None
    venue_profile_id: str | None = None
    nda_config: NDAConfig | None = None


class TagsUpdate(BaseModel):
    """Input for updating project tags."""
    tags: list[str]


class CategoryUpdate(BaseModel):
    """Input for setting project category."""
    category: str


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
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    starred: bool = False
    abstract: str = ""
    word_count: int = 0
    figure_count: int = 0
    quality_score: float | None = None
    total_cost_usd: float = 0.0
    created_at: str = ""
    updated_at: str = ""


class ProjectSummary(BaseModel):
    """Condensed project for list views."""
    id: str
    title: str
    venue_profile_id: str | None = None
    status: str
    revision_cycles: int = 0
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    starred: bool = False
    abstract: str = ""
    word_count: int = 0
    figure_count: int = 0
    quality_score: float | None = None
    total_cost_usd: float = 0.0
    created_at: str
    updated_at: str


class LibraryStats(BaseModel):
    """Aggregate statistics for the library view."""
    total_projects: int = 0
    by_venue: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_status_group: dict[str, int] = Field(default_factory=dict)
    avg_quality: float = 0.0
    total_cost: float = 0.0
    total_words: int = 0
    total_figures: int = 0
    top_tags: list[dict[str, Any]] = Field(default_factory=list)
