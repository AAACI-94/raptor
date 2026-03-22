"""Venue profile domain models."""

from pydantic import BaseModel, Field
from typing import Any


class RubricDimension(BaseModel):
    """A single quality dimension within a rubric."""
    name: str
    description: str
    weight: float
    min_passing: float = 5.0
    scoring_guide: dict[str, str] = Field(default_factory=dict)


class QualityRubric(BaseModel):
    """Venue-specific quality scoring framework."""
    dimensions: list[RubricDimension]
    passing_threshold: float = 7.0
    scale_min: int = 1
    scale_max: int = 10


class SectionTemplate(BaseModel):
    """Required or optional section in a venue template."""
    name: str
    min_words: int | None = None
    max_words: int | None = None
    required: bool = True


class StructuralTemplate(BaseModel):
    """Venue-specific document structure."""
    required_sections: list[SectionTemplate] = Field(default_factory=list)
    optional_sections: list[SectionTemplate] = Field(default_factory=list)
    section_order_constraints: str = ""
    total_length_min_pages: int | None = None
    total_length_max_pages: int | None = None
    total_length_target_pages: int | None = None


class ToneProfile(BaseModel):
    """Writing tone configuration per venue."""
    model_config = {"populate_by_name": True}

    register: str = "practitioner_direct"  # noqa: Pydantic shadow warning is acceptable
    person: str = "second_person_acceptable"
    voice: str = "active_preferred"
    jargon_level: str = "domain_standard"
    examples_required: bool = True
    code_samples_welcome: bool = True


class CitationFormat(BaseModel):
    """Citation formatting rules per venue."""
    style: str = "numbered_inline"
    format_spec: str = ""
    minimum_references: int = 10
    preferred_source_types: list[str] = Field(default_factory=list)


class ReviewPersona(BaseModel):
    """Simulated reviewer persona for the Critical Reviewer."""
    description: str = ""
    common_feedback_patterns: list[str] = Field(default_factory=list)


class VenueProfileData(BaseModel):
    """Full venue profile including all configuration."""
    structural_template: StructuralTemplate = Field(default_factory=StructuralTemplate)
    quality_rubric: QualityRubric
    tone_profile: ToneProfile = Field(default_factory=ToneProfile)
    citation_format: CitationFormat = Field(default_factory=CitationFormat)
    review_simulation_persona: ReviewPersona = Field(default_factory=ReviewPersona)
    nda_sensitivity_level: str = "moderate"
    nda_description: str = ""


class VenueProfile(BaseModel):
    """Full venue profile representation."""
    id: str
    venue_type: str
    display_name: str
    description: str = ""
    profile_data: VenueProfileData
    is_custom: bool = False
    created_at: str = ""
    updated_at: str = ""


class VenueCreate(BaseModel):
    """Input for creating a custom venue profile."""
    id: str
    venue_type: str
    display_name: str
    description: str = ""
    profile_data: VenueProfileData


class VenueUpdate(BaseModel):
    """Input for updating a venue profile."""
    display_name: str | None = None
    description: str | None = None
    profile_data: VenueProfileData | None = None
