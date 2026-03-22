"""Agent 3: Domain Writer.

Drafts sections grounded in the research corpus. Maintains voice consistency per venue.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

WRITER_SYSTEM = """Domain Writer for RAPTOR, a multi-agent research authoring platform for cybersecurity.

Your job: Draft paper sections grounded in the research corpus, following the outline structure
and venue-specific tone requirements.

For each section, you must:
1. Write the full prose content
2. Include inline source attribution (cite by [number] or author depending on venue)
3. Flag confidence levels: [WELL-SUPPORTED], [PARTIALLY-SUPPORTED], [AUTHOR-ASSERTION]
4. Flag any content that may need NDA generalization with [NDA-FLAG]

Output valid JSON:
{
  "sections": [
    {
      "section_name": "Introduction",
      "content": "Full prose content with citations...",
      "word_count": 450,
      "citations_used": ["Source Title 1", "Source Title 2"],
      "confidence_flags": {
        "well_supported": 5,
        "partially_supported": 2,
        "author_assertion": 1
      },
      "nda_flags": []
    }
  ],
  "total_word_count": 5200,
  "tone_consistency_notes": "How tone was maintained across sections"
}

REJECTION CRITERIA:
- Section lacks sufficient evidence from the research corpus
- Tone mismatches venue profile
- Section exceeds length constraints without proportional value
- NDA filter flags content that cannot be safely generalized
"""

REFLECTION_PROMPT = """Is every factual claim attributed to a source? Does the tone match
venue expectations? Would a domain expert find any claims unsupported or misleading?"""


class DomainWriter(BaseAgent):
    """Drafts all sections grounded in research, following the outline."""

    role = AgentRole.DOMAIN_WRITER
    artifact_type = ArtifactType.SECTION_DRAFT

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Starting draft...", 5)

        # Get upstream artifacts
        outline = artifact_service.get_latest_artifact(project.id, ArtifactType.OUTLINE)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        if not outline:
            raise ValueError("No outline found. Run structure stage first.")

        # Build tone instructions
        tone_instructions = ""
        if venue and venue.profile_data.tone_profile:
            tp = venue.profile_data.tone_profile
            tone_instructions = f"""Tone: {tp.register}
Person: {tp.person}
Voice: {tp.voice}
Jargon: {tp.jargon_level}
Examples required: {tp.examples_required}
Code samples: {tp.code_samples_welcome}"""

        # Build citation format
        cite_fmt = ""
        if venue and venue.profile_data.citation_format:
            cf = venue.profile_data.citation_format
            cite_fmt = f"Citation style: {cf.style} ({cf.format_spec}). Minimum {cf.minimum_references} references."

        user_msg = f"""## Outline
{json.dumps(outline.payload, indent=2)[:5000]}

## Research Sources
{json.dumps(research.payload.get('sources', []), indent=2)[:5000] if research else 'No sources available'}

## Author Context
{project.author_context or 'None provided'}

## Tone Requirements
{tone_instructions or 'Default professional tone'}

## Citation Format
{cite_fmt or 'Use numbered inline citations'}

## Instructions
Draft ALL sections from the outline. For each section:
- Follow the acceptance criteria
- Stay within word count bounds
- Cite sources inline
- Flag confidence levels
- Flag NDA-sensitive content

Respond with the JSON structure from your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=WRITER_SYSTEM,
            project_id=project.id,
            operation="draft_sections",
            max_tokens=16384,
            temperature=0.8,
        )

        await self.broadcast_progress(project.id, "Parsing draft...", 75)
        payload = self._parse_output(result["content"])

        section_count = len(payload.get("sections", []))
        total_words = payload.get("total_word_count", 0)
        self.log_decision(
            project.id,
            decision=f"Drafted {section_count} sections, {total_words} total words",
            rationale=payload.get("tone_consistency_notes", ""),
            confidence=0.8,
        )

        await self.broadcast_progress(project.id, "Self-reflection...", 90)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, "Draft complete", 100)

        metadata = ArtifactMetadata(
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            duration_ms=result["duration_ms"],
            estimated_cost_usd=result["cost_usd"],
        )

        return self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            target_agent=AgentRole.CRITICAL_REVIEWER,
            reflection_result=reflection,
        )

    def _parse_output(self, content: str) -> dict:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        return {"sections": [], "raw_content": content}
