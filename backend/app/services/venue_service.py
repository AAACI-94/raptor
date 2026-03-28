"""Publication target profile CRUD and default seeding.

UI refers to these as "Publication Targets". DB schema retains venue_profile_id column names.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_db, safe_update
from app.models.venue import (
    VenueProfile, VenueProfileData, VenueCreate, VenueUpdate,
    QualityRubric, RubricDimension, StructuralTemplate, SectionTemplate,
    ToneProfile, CitationFormat, ReviewPersona,
)

logger = logging.getLogger(__name__)


def seed_default_venues() -> None:
    """Seed built-in publication target profiles if they don't exist."""
    db = get_db()
    existing = db.execute("SELECT COUNT(*) as cnt FROM venue_profiles").fetchone()["cnt"]
    if existing > 0:
        return

    for venue in DEFAULT_VENUES:
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """INSERT INTO venue_profiles (id, venue_type, display_name, description, profile_data, is_custom, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (venue["id"], venue["venue_type"], venue["display_name"], venue["description"],
             json.dumps(venue["profile_data"]), now, now),
        )

    db.commit()
    logger.info("[venue] Seeded %d default venue profiles", len(DEFAULT_VENUES))


def get_venue(venue_id: str) -> VenueProfile:
    """Get a publication target profile by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM venue_profiles WHERE id = ?", (venue_id,)).fetchone()
    if row is None:
        raise ValueError(f"Venue not found: {venue_id}")
    return _row_to_venue(row)


def list_venues() -> list[VenueProfile]:
    """List all publication target profiles."""
    db = get_db()
    rows = db.execute("SELECT * FROM venue_profiles ORDER BY display_name").fetchall()
    return [_row_to_venue(r) for r in rows]


def create_venue(data: VenueCreate) -> VenueProfile:
    """Create a custom publication target profile."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO venue_profiles (id, venue_type, display_name, description, profile_data, is_custom, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
        (data.id, data.venue_type, data.display_name, data.description,
         json.dumps(data.profile_data.model_dump()), now, now),
    )
    db.commit()
    logger.info("[venue] Created custom venue %s: %s", data.id, data.display_name)
    return get_venue(data.id)


def update_venue(venue_id: str, data: VenueUpdate) -> VenueProfile:
    """Update a publication target profile."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    venue = get_venue(venue_id)

    updates: dict = {}
    if data.display_name is not None:
        updates["display_name"] = data.display_name
    if data.description is not None:
        updates["description"] = data.description
    if data.profile_data is not None:
        updates["profile_data"] = json.dumps(data.profile_data.model_dump())

    if updates:
        updates["updated_at"] = now
        _VENUE_UPDATE_COLUMNS = {"display_name", "description", "profile_data", "updated_at"}
        safe_update("venue_profiles", updates, "id", venue_id, _VENUE_UPDATE_COLUMNS)

    return get_venue(venue_id)


def delete_venue(venue_id: str) -> None:
    """Delete a custom publication target profile. Cannot delete built-in profiles."""
    db = get_db()
    row = db.execute("SELECT is_custom FROM venue_profiles WHERE id = ?", (venue_id,)).fetchone()
    if row is None:
        raise ValueError(f"Venue not found: {venue_id}")
    if not row["is_custom"]:
        raise ValueError("Cannot delete built-in publication target profiles")
    db.execute("DELETE FROM venue_profiles WHERE id = ?", (venue_id,))
    db.commit()
    logger.info("[venue] Deleted venue %s", venue_id)


def _row_to_venue(row) -> VenueProfile:
    return VenueProfile(
        id=row["id"],
        venue_type=row["venue_type"],
        display_name=row["display_name"],
        description=(row["description"] if row["description"] else ""),
        profile_data=VenueProfileData(**json.loads(row["profile_data"])),
        is_custom=bool(row["is_custom"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---- Default Venue Profiles ----

_SANS_RUBRIC = QualityRubric(
    dimensions=[
        RubricDimension(name="novelty", description="Does this contribute something new to the field?", weight=0.08, min_passing=5),
        RubricDimension(name="rigor", description="Is the methodology sound and reproducible?", weight=0.12, min_passing=6),
        RubricDimension(name="practitioner_utility", description="Can a practitioner apply this Monday morning?", weight=0.25, min_passing=7),
        RubricDimension(name="evidence_quality", description="Are claims supported by 2+ independent sources? Are sources primary or secondary?", weight=0.18, min_passing=6),
        RubricDimension(name="argumentative_rigor", description="Are causal claims logically valid? Do arguments have warrants, not just claims+data? Are fallacies absent? Are counterarguments addressed?", weight=0.15, min_passing=6),
        RubricDimension(name="accessibility", description="Is the writing clear and jargon-appropriate?", weight=0.12, min_passing=6),
        RubricDimension(name="completeness", description="Are all aspects of the topic adequately covered?", weight=0.10, min_passing=5),
    ],
    passing_threshold=7.0,
).model_dump()

_IEEE_RUBRIC = QualityRubric(
    dimensions=[
        RubricDimension(name="novelty", description="Is the contribution genuinely novel?", weight=0.20, min_passing=7),
        RubricDimension(name="rigor", description="Is the evaluation methodology sound?", weight=0.20, min_passing=7),
        RubricDimension(name="argumentative_rigor", description="Are causal claims valid (mechanism stated, confounds addressed, comparison group present)? Are logical fallacies absent? Do arguments follow Toulmin structure?", weight=0.15, min_passing=7),
        RubricDimension(name="evidence_quality", description="Is related work comprehensive? Are sources primary? Does the two-source rule hold?", weight=0.15, min_passing=6),
        RubricDimension(name="technical_depth", description="Is the technical contribution deep enough?", weight=0.15, min_passing=6),
        RubricDimension(name="accessibility", description="Is the writing clear for the audience?", weight=0.10, min_passing=5),
        RubricDimension(name="completeness", description="Are evaluation and discussion thorough?", weight=0.05, min_passing=5),
    ],
    passing_threshold=7.5,
).model_dump()

_INDUSTRY_RUBRIC = QualityRubric(
    dimensions=[
        RubricDimension(name="accessibility", description="Will this engage a broad audience without being shallow?", weight=0.25, min_passing=7),
        RubricDimension(name="practitioner_utility", description="Does it provide actionable takeaways?", weight=0.20, min_passing=6),
        RubricDimension(name="evidence_quality", description="Is the expertise credible? Are sources identified?", weight=0.15, min_passing=6),
        RubricDimension(name="argumentative_rigor", description="Are claims logically sound? Are causal arguments valid? Are obvious fallacies absent?", weight=0.15, min_passing=5),
        RubricDimension(name="novelty", description="Does it offer a fresh perspective?", weight=0.15, min_passing=5),
        RubricDimension(name="completeness", description="Is the topic adequately covered for the length?", weight=0.10, min_passing=5),
    ],
    passing_threshold=6.5,
).model_dump()

_SELF_PUB_RUBRIC = QualityRubric(
    dimensions=[
        RubricDimension(name="accessibility", description="Is the writing engaging and clear?", weight=0.20, min_passing=6),
        RubricDimension(name="practitioner_utility", description="Does it provide value to the reader?", weight=0.20, min_passing=6),
        RubricDimension(name="evidence_quality", description="Are assertions backed by evidence?", weight=0.20, min_passing=5),
        RubricDimension(name="argumentative_rigor", description="Are claims logically coherent? No obvious fallacies? Does the argument hold together?", weight=0.15, min_passing=5),
        RubricDimension(name="novelty", description="Does it offer a unique viewpoint?", weight=0.15, min_passing=5),
        RubricDimension(name="completeness", description="Does it have a clear thesis-evidence-conclusion arc?", weight=0.10, min_passing=5),
    ],
    passing_threshold=6.0,
).model_dump()


DEFAULT_VENUES = [
    {
        "id": "sans_reading_room",
        "venue_type": "practitioner_repository",
        "display_name": "SANS Reading Room",
        "description": "SANS Institute practitioner paper repository. Practitioner utility weighted highest.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Executive Summary", "min_words": 150, "max_words": 300, "required": True},
                    {"name": "Introduction", "min_words": 300, "max_words": 600, "required": True},
                    {"name": "Problem Statement", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "Methodology", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Findings", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Recommendations", "min_words": 500, "max_words": 1000, "required": True},
                    {"name": "Conclusion", "min_words": 200, "max_words": 400, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [
                    {"name": "Appendix", "min_words": None, "max_words": None, "required": False},
                    {"name": "About the Author", "min_words": 50, "max_words": 200, "required": False},
                ],
                "section_order_constraints": "Executive Summary must be first. References must be last. Findings must follow Methodology.",
                "total_length_min_pages": 8,
                "total_length_max_pages": 25,
                "total_length_target_pages": 15,
            },
            "quality_rubric": _SANS_RUBRIC,
            "tone_profile": {"register": "practitioner_direct", "person": "second_person_acceptable", "voice": "active_preferred", "jargon_level": "domain_standard", "examples_required": True, "code_samples_welcome": True},
            "citation_format": {"style": "numbered_inline", "format_spec": "IEEE-like numbered references", "minimum_references": 10, "preferred_source_types": ["peer_reviewed", "industry_report", "vendor_research", "standards_body"]},
            "review_simulation_persona": {"description": "A senior security practitioner who has read hundreds of SANS papers. Values practical applicability above theoretical contribution.", "common_feedback_patterns": ["How would I actually implement this?", "What tools/commands would I use?", "Show me the before/after metrics", "This is too theoretical, give me a case study"]},
            "nda_sensitivity_level": "moderate",
            "nda_description": "Generalize client names and specific metrics. Industry verticals and approximate improvements are acceptable.",
        },
    },
    {
        "id": "ieee_sp",
        "venue_type": "academic_conference",
        "display_name": "IEEE S&P",
        "description": "IEEE Symposium on Security and Privacy. Top-tier academic venue. Novelty and rigor weighted highest.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Abstract", "min_words": 150, "max_words": 250, "required": True},
                    {"name": "Introduction", "min_words": 500, "max_words": 1000, "required": True},
                    {"name": "Related Work", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Methodology", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Evaluation", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Discussion", "min_words": 300, "max_words": 800, "required": True},
                    {"name": "Conclusion", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [],
                "section_order_constraints": "Abstract first. Related Work before Methodology. Evaluation follows Methodology.",
                "total_length_min_pages": 10,
                "total_length_max_pages": 13,
                "total_length_target_pages": 12,
            },
            "quality_rubric": _IEEE_RUBRIC,
            "tone_profile": {"register": "academic_formal", "person": "third_person", "voice": "passive_acceptable", "jargon_level": "technical_precise", "examples_required": False, "code_samples_welcome": False},
            "citation_format": {"style": "numbered_inline", "format_spec": "IEEE citation format", "minimum_references": 25, "preferred_source_types": ["peer_reviewed", "preprint"]},
            "review_simulation_persona": {"description": "An academic reviewer on IEEE S&P PC. Expects novel contributions with rigorous evaluation.", "common_feedback_patterns": ["What is the novelty over prior work?", "The evaluation methodology needs strengthening", "The threat model is incomplete", "How does this compare to [baseline]?"]},
            "nda_sensitivity_level": "high",
            "nda_description": "Academic papers should not contain any client-specific information.",
        },
    },
    {
        "id": "acm_ccs",
        "venue_type": "academic_conference",
        "display_name": "ACM CCS",
        "description": "ACM Conference on Computer and Communications Security. Top-tier. Strong related work section critical.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Abstract", "min_words": 150, "max_words": 250, "required": True},
                    {"name": "Introduction", "min_words": 500, "max_words": 1000, "required": True},
                    {"name": "Background", "min_words": 300, "max_words": 800, "required": True},
                    {"name": "Related Work", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "System Design", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Implementation", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Evaluation", "min_words": 1000, "max_words": 2500, "required": True},
                    {"name": "Discussion", "min_words": 300, "max_words": 800, "required": True},
                    {"name": "Conclusion", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [],
                "section_order_constraints": "Abstract first. Background before Related Work. Evaluation after Implementation.",
                "total_length_min_pages": 10,
                "total_length_max_pages": 15,
                "total_length_target_pages": 12,
            },
            "quality_rubric": _IEEE_RUBRIC,
            "tone_profile": {"register": "academic_formal", "person": "third_person", "voice": "passive_acceptable", "jargon_level": "technical_precise", "examples_required": False, "code_samples_welcome": True},
            "citation_format": {"style": "author_year", "format_spec": "ACM citation format", "minimum_references": 30, "preferred_source_types": ["peer_reviewed", "preprint"]},
            "review_simulation_persona": {"description": "An ACM CCS PC member. Values systems contributions with strong implementation and evaluation.", "common_feedback_patterns": ["The related work section misses key references", "Is the implementation publicly available?", "How does this scale?", "The security analysis needs formal treatment"]},
            "nda_sensitivity_level": "high",
            "nda_description": "No client-specific data in academic submissions.",
        },
    },
    {
        "id": "dark_reading",
        "venue_type": "industry_publication",
        "display_name": "Dark Reading",
        "description": "Industry cybersecurity publication. Accessibility highest. Hook-driven structure.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Hook", "min_words": 50, "max_words": 150, "required": True},
                    {"name": "Problem", "min_words": 200, "max_words": 400, "required": True},
                    {"name": "Analysis", "min_words": 400, "max_words": 800, "required": True},
                    {"name": "Recommendations", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "Conclusion", "min_words": 50, "max_words": 150, "required": True},
                ],
                "optional_sections": [],
                "section_order_constraints": "Hook must be first.",
                "total_length_min_pages": None,
                "total_length_max_pages": None,
                "total_length_target_pages": None,
            },
            "quality_rubric": _INDUSTRY_RUBRIC,
            "tone_profile": {"register": "industry_accessible", "person": "second_person_preferred", "voice": "active_preferred", "jargon_level": "accessible_technical", "examples_required": True, "code_samples_welcome": False},
            "citation_format": {"style": "hyperlink_inline", "format_spec": "Inline hyperlinks to sources", "minimum_references": 3, "preferred_source_types": ["industry_report", "vendor_research", "news"]},
            "review_simulation_persona": {"description": "An industry editor focused on engagement and credibility.", "common_feedback_patterns": ["Is the hook compelling enough?", "Will this get clicks without being clickbait?", "Can you add a real-world example?", "Simplify the technical jargon"]},
            "nda_sensitivity_level": "moderate",
            "nda_description": "Generalize client names. Industry examples are fine.",
        },
    },
    {
        "id": "linkedin_article",
        "venue_type": "self_published",
        "display_name": "LinkedIn Article",
        "description": "Self-published thought leadership. First-person acceptable. 1000-3000 words.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Opening Hook", "min_words": 50, "max_words": 200, "required": True},
                    {"name": "Thesis", "min_words": 100, "max_words": 300, "required": True},
                    {"name": "Evidence & Analysis", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Practical Takeaways", "min_words": 200, "max_words": 600, "required": True},
                    {"name": "Call to Action", "min_words": 50, "max_words": 150, "required": True},
                ],
                "optional_sections": [],
                "section_order_constraints": "Opening Hook first. Call to Action last.",
                "total_length_min_pages": None,
                "total_length_max_pages": None,
                "total_length_target_pages": None,
            },
            "quality_rubric": _SELF_PUB_RUBRIC,
            "tone_profile": {"register": "thought_leadership", "person": "first_person", "voice": "active_preferred", "jargon_level": "accessible", "examples_required": True, "code_samples_welcome": False},
            "citation_format": {"style": "hyperlink_inline", "format_spec": "Inline hyperlinks", "minimum_references": 2, "preferred_source_types": ["industry_report", "news", "blog"]},
            "review_simulation_persona": {"description": "A LinkedIn reader who scrolls fast. Needs to be hooked in the first two sentences.", "common_feedback_patterns": ["Would I stop scrolling for this?", "Is the author voice authentic?", "Where is the unique insight?", "Too long for LinkedIn"]},
            "nda_sensitivity_level": "low",
            "nda_description": "Personal opinions and general industry observations are fine.",
        },
    },
    {
        "id": "usenix_security",
        "venue_type": "academic_conference",
        "display_name": "USENIX Security",
        "description": "USENIX Security Symposium. Systems-oriented. Implementation details valued. Artifact evaluation track.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Abstract", "min_words": 150, "max_words": 250, "required": True},
                    {"name": "Introduction", "min_words": 500, "max_words": 1000, "required": True},
                    {"name": "Background & Motivation", "min_words": 400, "max_words": 1000, "required": True},
                    {"name": "Design", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Implementation", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Evaluation", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Related Work", "min_words": 500, "max_words": 1000, "required": True},
                    {"name": "Conclusion", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [
                    {"name": "Artifact Appendix", "min_words": None, "max_words": None, "required": False},
                ],
                "section_order_constraints": "Abstract first. Design before Implementation. Related Work can be before Conclusion.",
                "total_length_min_pages": 12,
                "total_length_max_pages": 18,
                "total_length_target_pages": 15,
            },
            "quality_rubric": _IEEE_RUBRIC,
            "tone_profile": {"register": "academic_formal", "person": "third_person", "voice": "active_preferred", "jargon_level": "technical_precise", "examples_required": False, "code_samples_welcome": True},
            "citation_format": {"style": "numbered_inline", "format_spec": "USENIX citation format", "minimum_references": 25, "preferred_source_types": ["peer_reviewed", "preprint"]},
            "review_simulation_persona": {"description": "A USENIX reviewer who values practical systems contributions with artifact evaluation.", "common_feedback_patterns": ["Is the source code available?", "Can I reproduce these results?", "What is the deployment overhead?", "How does this compare in performance?"]},
            "nda_sensitivity_level": "high",
            "nda_description": "No proprietary data in academic venues.",
        },
    },
    {
        "id": "csa_research",
        "venue_type": "industry_publication",
        "display_name": "CSA Research",
        "description": "Cloud Security Alliance research. Framework-oriented. Governance focus.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Executive Summary", "min_words": 200, "max_words": 500, "required": True},
                    {"name": "Introduction", "min_words": 300, "max_words": 600, "required": True},
                    {"name": "Background", "min_words": 300, "max_words": 800, "required": True},
                    {"name": "Framework Analysis", "min_words": 1000, "max_words": 3000, "required": True},
                    {"name": "Recommendations", "min_words": 500, "max_words": 1500, "required": True},
                    {"name": "Conclusion", "min_words": 200, "max_words": 400, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [
                    {"name": "Appendix", "min_words": None, "max_words": None, "required": False},
                ],
                "section_order_constraints": "Executive Summary first. Framework Analysis is the core.",
                "total_length_min_pages": 10,
                "total_length_max_pages": 30,
                "total_length_target_pages": 20,
            },
            "quality_rubric": _INDUSTRY_RUBRIC,
            "tone_profile": {"register": "governance_formal", "person": "third_person", "voice": "active_preferred", "jargon_level": "governance_standard", "examples_required": True, "code_samples_welcome": False},
            "citation_format": {"style": "numbered_inline", "format_spec": "Numbered references", "minimum_references": 15, "preferred_source_types": ["standards_body", "peer_reviewed", "industry_report"]},
            "review_simulation_persona": {"description": "A CSA reviewer focused on governance applicability and framework alignment.", "common_feedback_patterns": ["How does this map to existing CSA guidance?", "What is the governance implication?", "Can enterprises adopt this today?", "Where are the compliance touchpoints?"]},
            "nda_sensitivity_level": "moderate",
            "nda_description": "Generalize client names. Framework-level analysis is preferred.",
        },
    },
    {
        "id": "acsac",
        "venue_type": "academic_conference",
        "display_name": "ACSAC",
        "description": "Annual Computer Security Applications Conference. Mid-tier academic. Strong practitioner bridge.",
        "profile_data": {
            "structural_template": {
                "required_sections": [
                    {"name": "Abstract", "min_words": 150, "max_words": 250, "required": True},
                    {"name": "Introduction", "min_words": 400, "max_words": 800, "required": True},
                    {"name": "Related Work", "min_words": 400, "max_words": 1000, "required": True},
                    {"name": "Approach", "min_words": 800, "max_words": 2000, "required": True},
                    {"name": "Evaluation", "min_words": 800, "max_words": 2000, "required": True},
                    {"name": "Discussion", "min_words": 200, "max_words": 600, "required": True},
                    {"name": "Conclusion", "min_words": 150, "max_words": 400, "required": True},
                    {"name": "References", "min_words": None, "max_words": None, "required": True},
                ],
                "optional_sections": [],
                "section_order_constraints": "Abstract first. Standard academic ordering.",
                "total_length_min_pages": 8,
                "total_length_max_pages": 10,
                "total_length_target_pages": 10,
            },
            "quality_rubric": _IEEE_RUBRIC,
            "tone_profile": {"register": "academic_accessible", "person": "third_person", "voice": "active_preferred", "jargon_level": "technical_precise", "examples_required": True, "code_samples_welcome": True},
            "citation_format": {"style": "numbered_inline", "format_spec": "ACM/IEEE hybrid format", "minimum_references": 20, "preferred_source_types": ["peer_reviewed", "industry_report"]},
            "review_simulation_persona": {"description": "An ACSAC reviewer who values practical security contributions with academic rigor.", "common_feedback_patterns": ["Does this bridge theory and practice?", "Is there a deployable component?", "The novelty bar is moderate but real", "Practitioners should be able to benefit"]},
            "nda_sensitivity_level": "high",
            "nda_description": "Academic venue; no proprietary information.",
        },
    },
]
