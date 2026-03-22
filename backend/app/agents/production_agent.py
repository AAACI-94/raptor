"""Agent 5: Production Agent.

Takes approved content and produces publish-ready artifacts.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

PRODUCTION_SYSTEM = """Production Agent for RAPTOR, a multi-agent research authoring platform.

Your job: Take approved draft sections and produce a final, formatted document ready for
submission or publication.

You must:
1. Assemble all sections into a coherent document
2. Generate a properly formatted bibliography/references section
3. Ensure consistent formatting throughout
4. Create a submission checklist for the target venue
5. Flag any formatting issues

Output valid JSON:
{
  "document": {
    "title": "Paper title",
    "abstract": "Abstract text if required by venue",
    "sections": [
      {
        "heading": "Section heading",
        "content": "Final formatted content",
        "level": 1
      }
    ],
    "references": [
      {
        "number": 1,
        "formatted": "[1] A. Author, 'Title,' in Proc. Conf, 2025, pp. 1-10.",
        "source_title": "Original source title"
      }
    ]
  },
  "submission_checklist": [
    {"item": "Abstract within 250 word limit", "status": "pass", "detail": "238 words"},
    {"item": "Page count within limit", "status": "pass", "detail": "12 pages"},
    {"item": "All references properly formatted", "status": "warning", "detail": "Reference 7 missing DOI"}
  ],
  "formatting_notes": "Any issues or notes about the formatted document",
  "total_word_count": 5200,
  "estimated_pages": 12
}
"""

REFLECTION_PROMPT = """Does this document meet all formatting requirements for the target venue?
Are all references properly formatted and cross-referenced? Would this pass a desk check
at submission?"""


class ProductionAgent(BaseAgent):
    """Produces formatted, publish-ready documents from approved drafts."""

    role = AgentRole.PRODUCTION_AGENT
    artifact_type = ArtifactType.PRODUCTION_OUTPUT

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Starting document production...", 5)

        # Get the approved draft
        draft = artifact_service.get_latest_artifact(project.id, ArtifactType.SECTION_DRAFT)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        if not draft:
            raise ValueError("No draft found.")

        # Citation format from venue
        cite_info = ""
        if venue and venue.profile_data.citation_format:
            cf = venue.profile_data.citation_format
            cite_info = f"Citation style: {cf.style}\nFormat: {cf.format_spec}\nMinimum references: {cf.minimum_references}"

        user_msg = f"""## Draft Sections
{json.dumps(draft.payload, indent=2)[:8000]}

## Research Sources
{json.dumps(research.payload.get('sources', []), indent=2)[:3000] if research else '[]'}

## Target Venue: {venue.display_name if venue else 'General'}

## Citation Format
{cite_info or 'Use numbered IEEE-style citations'}

## Paper Title: {project.title}

## Instructions
1. Assemble all sections into final document order
2. Format the bibliography with proper citation style
3. Ensure internal consistency (no contradicting statements across sections)
4. Generate a venue-specific submission checklist
5. Report total word count and estimated page count

Respond with the JSON structure from your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=PRODUCTION_SYSTEM,
            project_id=project.id,
            operation="produce_document",
            max_tokens=16384,
        )

        await self.broadcast_progress(project.id, "Parsing production output...", 75)
        payload = self._parse_output(result["content"])

        self.log_decision(
            project.id,
            decision=f"Produced document: {payload.get('total_word_count', 0)} words, ~{payload.get('estimated_pages', 0)} pages",
            rationale=payload.get("formatting_notes", ""),
            confidence=0.9,
        )

        # Self-reflection
        await self.broadcast_progress(project.id, "Self-reflection...", 90)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, "Document production complete", 100)

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
        return {"document": {"sections": []}, "raw_content": content}
