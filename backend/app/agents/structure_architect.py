"""Agent 2: Structure Architect.

Takes research plan, produces venue-appropriate outline with section-level acceptance criteria.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

STRUCTURE_SYSTEM = """Structure Architect for RAPTOR, a multi-agent research authoring platform.

Your job: Take a research plan and contribution claim, produce a venue-appropriate outline
with section-level acceptance criteria.

You must output valid JSON with this structure:
{
  "outline": [
    {
      "section_name": "Section Title",
      "required": true,
      "order": 1,
      "min_words": 300,
      "max_words": 800,
      "acceptance_criteria": [
        "Must introduce the problem with a compelling hook",
        "Must state the contribution claim clearly"
      ],
      "assigned_sources": ["source_title_1", "source_title_2"],
      "subsections": [
        {
          "name": "Subsection Title",
          "guidance": "What this subsection should cover"
        }
      ]
    }
  ],
  "structural_rationale": "Why this organization serves the argument",
  "dependency_map": {
    "Section A": ["references Section B findings"]
  },
  "total_estimated_words": 5000,
  "total_estimated_pages": 12
}

REJECTION CRITERIA:
- Research plan doesn't map to a coherent paper structure
- Missing required sections for target venue
- Contribution claim requires evaluation methodology the author cannot produce
- Structural dependencies create circular references
"""

REFLECTION_PROMPT = """Does this outline have a clear argument arc from introduction to conclusion?
Does every section serve the contribution claim? Would a reviewer at the target venue identify
any structural gaps?"""


class StructureArchitect(BaseAgent):
    """Produces a venue-appropriate document outline from the research plan."""

    role = AgentRole.STRUCTURE_ARCHITECT
    artifact_type = ArtifactType.OUTLINE

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Generating outline...", 10)

        # Get the research plan artifact
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)
        if not research:
            raise ValueError("No research plan found. Run research stage first.")

        # Build venue section requirements
        venue_sections = ""
        if venue and venue.profile_data.structural_template:
            tmpl = venue.profile_data.structural_template
            required = [f"- {s.name} ({s.min_words}-{s.max_words} words)" for s in tmpl.required_sections]
            optional = [f"- {s.name} (optional)" for s in tmpl.optional_sections]
            venue_sections = f"""Required sections:\n{"chr(10)".join(required)}\n\nOptional sections:\n{"chr(10)".join(optional)}\n\nOrder constraints: {tmpl.section_order_constraints}"""

        user_msg = f"""## Research Plan
{json.dumps(research.payload, indent=2)[:6000]}

## Target Venue: {venue.display_name if venue else 'Not specified'}

## Venue Section Requirements
{venue_sections or 'No specific requirements.'}

## Instructions
1. Design a section hierarchy that serves the contribution claim
2. Include all venue-required sections
3. Set word count targets per section
4. Define acceptance criteria for each section
5. Map research sources to sections
6. Explain the structural rationale

Respond with the JSON structure specified in your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=STRUCTURE_SYSTEM,
            project_id=project.id,
            operation="generate_outline",
            max_tokens=6144,
        )

        await self.broadcast_progress(project.id, "Parsing outline...", 70)

        payload = self._parse_output(result["content"])

        self.log_decision(
            project.id,
            decision=f"Generated outline with {len(payload.get('outline', []))} sections",
            rationale=payload.get("structural_rationale", ""),
            confidence=0.85,
        )

        # Self-reflection
        await self.broadcast_progress(project.id, "Self-reflection...", 85)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, "Outline complete", 100)

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
            target_agent=AgentRole.DOMAIN_WRITER,
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
        return {"outline": [], "raw_content": content}
