"""Agent 7: Visual Architect.

Analyzes draft sections and generates Mermaid diagrams that support the paper's claims.
Produces venue-appropriate figures: formal for academic, simplified for practitioner/blog.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

VISUAL_SYSTEM = """Visual Architect for RAPTOR, a multi-agent research authoring platform for cybersecurity.

Your job: Analyze the paper's draft sections and generate diagrams that visually support
the paper's key claims, architecture, and findings. Every figure must earn its place by
communicating something that prose alone cannot.

You output Mermaid diagram markup. Mermaid is rendered to SVG/PNG without external tools.

DIAGRAM TYPES you can generate:
- flowchart (attack flows, decision trees, process pipelines)
- sequenceDiagram (protocol interactions, attack sequences, agent communication)
- classDiagram (taxonomies, component relationships, type hierarchies)
- stateDiagram-v2 (state machines, lifecycle transitions)
- graph TD/LR (architecture diagrams, system overviews, network topologies)
- pie (distribution breakdowns)
- gantt (timelines, phased approaches)
- block-beta (block diagrams for system architecture)

VENUE ADAPTATION:
- Academic (IEEE, ACM, USENIX): Formal notation, precise labels, grayscale-safe, numbered figures
  with captions. Reference figures in text as "Figure N". Include data flow directions.
- Practitioner (SANS, CSA): Clear, actionable diagrams. Color-coded severity/priority.
  "Before/After" comparisons. Implementation-focused architecture diagrams.
- Industry (Dark Reading): Simple, high-impact visuals. Minimal technical notation.
  One key takeaway per figure.
- Self-published (LinkedIn): Eye-catching, shareable. Bold colors, minimal text.

CYBERSECURITY DIAGRAM CONVENTIONS:
- Red for attacker/threat paths, blue for defender/control paths
- Dashed lines for potential/optional flows, solid for confirmed
- Highlight trust boundaries with subgraph labels
- Use MITRE ATT&CK technique IDs where relevant (e.g., T1059)
- Mark "detection points" in defense diagrams

Output valid JSON:
{
  "figures": [
    {
      "figure_id": "fig-1",
      "title": "Figure 1: Agentic AI Attack Surface Taxonomy",
      "caption": "Classification of attack vectors across three categories...",
      "diagram_type": "flowchart",
      "mermaid": "flowchart TD\\n    A[Agentic AI Vulnerabilities] --> B[Tool-Use Abuse]\\n    ...",
      "placement": "Section 3, after paragraph discussing taxonomy",
      "supports_claim": "Three distinct attack surface categories exist",
      "venue_notes": "Grayscale-safe for IEEE print proceedings"
    }
  ],
  "figure_plan": "Rationale for figure selection and how they support the paper's argument arc",
  "cross_references": [
    {"figure_id": "fig-1", "section": "Introduction", "reference_text": "as shown in Figure 1"}
  ],
  "total_figures": 4,
  "venue_compliance_notes": "IEEE S&P typically expects 4-8 figures. Generated 4 core figures."
}

REJECTION CRITERIA:
- Figure doesn't support any claim in the paper text
- Figure duplicates information already clear from prose alone
- Figure complexity is inappropriate for the target venue
- Mermaid syntax is invalid or would not render
- Figure count is inappropriate for venue (too many for a blog, too few for IEEE)
"""

REFLECTION_PROMPT = """Does every figure support a specific claim from the draft?
Is the Mermaid syntax valid? Are the figures venue-appropriate in complexity and style?
Would a reviewer say 'this figure adds value beyond what the text says'?"""


class VisualArchitect(BaseAgent):
    """Generates Mermaid diagrams from draft content, venue-adapted."""

    role = AgentRole.VISUAL_ARCHITECT
    artifact_type = ArtifactType.FIGURES

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Analyzing draft for figure opportunities...", 5)

        # Get upstream artifacts
        draft = artifact_service.get_latest_artifact(project.id, ArtifactType.SECTION_DRAFT)
        outline = artifact_service.get_latest_artifact(project.id, ArtifactType.OUTLINE)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        if not draft:
            raise ValueError("No draft found. Run drafting stage first.")

        # Build venue-specific figure guidance
        venue_guidance = "General professional figures."
        expected_count = "3-5"
        if venue:
            vtype = venue.venue_type
            if vtype == "academic_conference":
                venue_guidance = f"Academic venue ({venue.display_name}). Formal notation, grayscale-safe, numbered figures with descriptive captions. Reference each figure in text."
                expected_count = "4-8"
            elif vtype == "practitioner_repository":
                venue_guidance = f"Practitioner venue ({venue.display_name}). Clear, actionable diagrams. Color-coded where helpful. Implementation-focused."
                expected_count = "3-6"
            elif vtype == "industry_publication":
                venue_guidance = f"Industry publication ({venue.display_name}). Simple, high-impact visuals. One takeaway per figure. Minimal technical notation."
                expected_count = "2-4"
            elif vtype == "self_published":
                venue_guidance = f"Self-published ({venue.display_name}). Eye-catching, shareable visuals. Bold, minimal text."
                expected_count = "1-3"

        # Extract key claims and structure from draft
        draft_summary = json.dumps(draft.payload, indent=2)[:6000]
        outline_summary = json.dumps(outline.payload, indent=2)[:2000] if outline else "No outline available"
        contribution = ""
        if research:
            contribution = research.payload.get("contribution_claim", "")

        await self.broadcast_progress(project.id, "Generating figures...", 20)

        user_msg = f"""## Paper Title: {project.title}

## Contribution Claim
{contribution or 'Not specified'}

## Outline
{outline_summary}

## Draft Sections
{draft_summary}

## Venue Guidance
{venue_guidance}
Expected figure count: {expected_count}

## Instructions
1. Identify the key concepts, architectures, taxonomies, and findings that benefit from visualization
2. For each, generate a Mermaid diagram with proper syntax
3. Write a descriptive caption for each figure
4. Specify where each figure should be placed in the paper
5. Map each figure to the claim it supports
6. Generate cross-reference text for inserting into the prose
7. Ensure all Mermaid syntax is valid and will render correctly

IMPORTANT: Use proper Mermaid syntax. Test mental rendering of each diagram.
Common patterns:
- flowchart TD for top-down flows
- sequenceDiagram for interactions
- classDiagram for taxonomies/relationships
- graph LR for left-to-right architectures

Respond with the JSON structure from your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=VISUAL_SYSTEM,
            project_id=project.id,
            operation="generate_figures",
            max_tokens=12288,
            temperature=0.7,
        )

        await self.broadcast_progress(project.id, "Parsing figures...", 70)
        payload = self._parse_output(result["content"])

        figure_count = len(payload.get("figures", []))
        figure_types = [f.get("diagram_type", "unknown") for f in payload.get("figures", [])]

        self.log_decision(
            project.id,
            decision=f"Generated {figure_count} figures: {', '.join(figure_types)}",
            rationale=payload.get("figure_plan", ""),
            confidence=0.85,
            alternatives=[f"Could generate {expected_count} figures per venue guidelines"],
        )

        # Validate Mermaid syntax (basic check)
        for fig in payload.get("figures", []):
            mermaid = fig.get("mermaid", "")
            if not mermaid or len(mermaid) < 20:
                self.logger.warning("[visual] Figure %s has very short/empty Mermaid", fig.get("figure_id"))

        # Self-reflection
        await self.broadcast_progress(project.id, "Self-reflection...", 85)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, f"Figures complete ({figure_count} generated)", 100)

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
        return {"figures": [], "raw_content": content}
