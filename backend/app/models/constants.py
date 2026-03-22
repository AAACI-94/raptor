"""Centralized constants and enums. Single source of truth for all string literals."""

from enum import StrEnum


class AgentRole(StrEnum):
    RESEARCH_STRATEGIST = "research_strategist"
    STRUCTURE_ARCHITECT = "structure_architect"
    DOMAIN_WRITER = "domain_writer"
    CRITICAL_REVIEWER = "critical_reviewer"
    PRODUCTION_AGENT = "production_agent"
    OBSERVATORY = "observatory"


class ProjectStatus(StrEnum):
    TOPIC_SELECTED = "TOPIC_SELECTED"
    RESEARCHING = "RESEARCHING"
    RESEARCH_COMPLETE = "RESEARCH_COMPLETE"
    STRUCTURING = "STRUCTURING"
    STRUCTURE_COMPLETE = "STRUCTURE_COMPLETE"
    DRAFTING = "DRAFTING"
    DRAFT_COMPLETE = "DRAFT_COMPLETE"
    REVIEWING = "REVIEWING"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    REVIEW_PASSED = "REVIEW_PASSED"
    PRODUCING = "PRODUCING"
    PRODUCTION_COMPLETE = "PRODUCTION_COMPLETE"
    PUBLISHED = "PUBLISHED"


class ArtifactType(StrEnum):
    RESEARCH_PLAN = "research_plan"
    OUTLINE = "outline"
    SECTION_DRAFT = "section_draft"
    REVIEW = "review"
    PRODUCTION_OUTPUT = "production_output"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class VenueType(StrEnum):
    PRACTITIONER_REPOSITORY = "practitioner_repository"
    ACADEMIC_CONFERENCE = "academic_conference"
    INDUSTRY_PUBLICATION = "industry_publication"
    SELF_PUBLISHED = "self_published"
    CUSTOM = "custom"


class SourceType(StrEnum):
    PEER_REVIEWED = "peer_reviewed"
    INDUSTRY_REPORT = "industry_report"
    VENDOR_RESEARCH = "vendor_research"
    STANDARDS_BODY = "standards_body"
    NEWS = "news"
    BLOG = "blog"
    BOOK = "book"
    PREPRINT = "preprint"


class QualityDimension(StrEnum):
    NOVELTY = "novelty"
    RIGOR = "rigor"
    PRACTITIONER_UTILITY = "practitioner_utility"
    EVIDENCE_QUALITY = "evidence_quality"
    ACCESSIBILITY = "accessibility"
    COMPLETENESS = "completeness"
    TECHNICAL_DEPTH = "technical_depth"
    VENUE_COMPLIANCE = "venue_compliance"


class NDAMode(StrEnum):
    FLAG = "flag"
    AUTO_GENERALIZE = "auto_generalize"
    BLOCK = "block"


# Valid pipeline transitions
VALID_TRANSITIONS: dict[ProjectStatus, list[ProjectStatus]] = {
    ProjectStatus.TOPIC_SELECTED: [ProjectStatus.RESEARCHING],
    ProjectStatus.RESEARCHING: [ProjectStatus.RESEARCH_COMPLETE],
    ProjectStatus.RESEARCH_COMPLETE: [ProjectStatus.STRUCTURING],
    ProjectStatus.STRUCTURING: [ProjectStatus.STRUCTURE_COMPLETE],
    ProjectStatus.STRUCTURE_COMPLETE: [ProjectStatus.DRAFTING],
    ProjectStatus.DRAFTING: [ProjectStatus.DRAFT_COMPLETE],
    ProjectStatus.DRAFT_COMPLETE: [ProjectStatus.REVIEWING],
    ProjectStatus.REVIEWING: [ProjectStatus.REVIEW_PASSED, ProjectStatus.REVISION_REQUESTED],
    ProjectStatus.REVISION_REQUESTED: [ProjectStatus.DRAFTING, ProjectStatus.STRUCTURING, ProjectStatus.RESEARCHING],
    ProjectStatus.REVIEW_PASSED: [ProjectStatus.PRODUCING],
    ProjectStatus.PRODUCING: [ProjectStatus.PRODUCTION_COMPLETE],
    ProjectStatus.PRODUCTION_COMPLETE: [ProjectStatus.PUBLISHED],
}

# Agent responsible for each status transition
STATUS_TO_AGENT: dict[ProjectStatus, AgentRole] = {
    ProjectStatus.RESEARCHING: AgentRole.RESEARCH_STRATEGIST,
    ProjectStatus.STRUCTURING: AgentRole.STRUCTURE_ARCHITECT,
    ProjectStatus.DRAFTING: AgentRole.DOMAIN_WRITER,
    ProjectStatus.REVIEWING: AgentRole.CRITICAL_REVIEWER,
    ProjectStatus.PRODUCING: AgentRole.PRODUCTION_AGENT,
}
