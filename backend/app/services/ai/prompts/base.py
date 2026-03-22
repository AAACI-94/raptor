"""Base prompt builder with cache-friendly ordering."""

from typing import Any


def build_system_prompt(
    role_description: str,
    venue_context: dict[str, Any] | None = None,
    domain_framework: str = "",
    rejection_criteria: str = "",
    self_reflection_prompt: str = "",
) -> str:
    """Build a system prompt following cache-friendly ordering.

    Stable content first (role, framework), dynamic content last (venue specifics).
    """
    sections = [
        f"You are the {role_description}.",
        "",
        "You are part of RAPTOR, a multi-agent research authoring platform for cybersecurity practitioners.",
        "Your output will be consumed by downstream agents. Produce structured, precise output.",
        "",
    ]

    if domain_framework:
        sections.append("## Domain Framework")
        sections.append(domain_framework)
        sections.append("")

    if rejection_criteria:
        sections.append("## Rejection Criteria")
        sections.append("You MUST reject the input if any of these conditions are met:")
        sections.append(rejection_criteria)
        sections.append("")

    if self_reflection_prompt:
        sections.append("## Self-Reflection")
        sections.append("Before submitting your output, evaluate it against this question:")
        sections.append(self_reflection_prompt)
        sections.append("")

    if venue_context:
        sections.append("## Target Venue")
        sections.append(f"Venue: {venue_context.get('display_name', 'Unknown')}")
        sections.append(f"Type: {venue_context.get('venue_type', 'Unknown')}")
        if venue_context.get("tone_profile"):
            tone = venue_context["tone_profile"]
            sections.append(f"Register: {tone.get('register', '')}")
            sections.append(f"Person: {tone.get('person', '')}")
            sections.append(f"Voice: {tone.get('voice', '')}")
        sections.append("")

    return "\n".join(sections)


def build_user_message(
    task: str,
    context: dict[str, Any] | None = None,
    evidence: list[dict] | None = None,
) -> str:
    """Build a user message with task and context."""
    parts = [task]

    if context:
        parts.append("\n## Context")
        for key, value in context.items():
            if isinstance(value, str):
                parts.append(f"**{key}:** {value}")
            else:
                import json
                parts.append(f"**{key}:** {json.dumps(value, indent=2)}")

    if evidence:
        parts.append("\n## Evidence")
        for i, source in enumerate(evidence, 1):
            parts.append(f"\n### Source {i}: {source.get('title', 'Untitled')}")
            if source.get("url"):
                parts.append(f"URL: {source['url']}")
            if source.get("content_summary"):
                parts.append(source["content_summary"])

    return "\n".join(parts)
