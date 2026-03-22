"""Agent 1: Research Strategist with Agentic RAG subsystem.

Plan-Retrieve-Evaluate-Reflect cycle for building a grounded research corpus.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services.ai.prompts.base import build_system_prompt, build_user_message

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM = """Research Strategist for RAPTOR, a multi-agent research authoring platform.

Your job: Given a topic and target venue, produce a comprehensive research plan.

You must output valid JSON with this structure:
{
  "contribution_claim": "The specific novel assertion this paper will make",
  "gap_analysis": "What exists in the literature vs. what's missing",
  "research_plan": [
    {
      "query": "search query to execute",
      "source_type": "academic|industry|standards|web",
      "rationale": "why this query will find relevant sources"
    }
  ],
  "sources": [
    {
      "title": "Source title",
      "url": "URL if available",
      "source_type": "peer_reviewed|industry_report|vendor_research|standards_body|blog|preprint",
      "relevance_score": 0.0-1.0,
      "authority_score": 0.0-1.0,
      "key_findings": "What this source contributes",
      "claims_supported": ["claim1", "claim2"]
    }
  ],
  "evidence_map": {
    "claim_text": ["source_title_1", "source_title_2"]
  },
  "venue_alignment": "How this research plan aligns with the target venue's expectations",
  "nda_flags": ["any potentially sensitive content areas"]
}

REJECTION CRITERIA (reject the input if any apply):
- Topic has insufficient novelty for the target venue
- Proposed contribution is too broad to be defensible in a single paper
- Topic requires proprietary data that cannot be generalized
"""

REFLECTION_PROMPT = """Does this research plan identify a specific, defensible contribution claim
supported by at least 5 quality sources? Would a reviewer at the target venue consider this gap
worth filling? Is the evidence map comprehensive?"""


class ResearchStrategist(BaseAgent):
    """Produces a research plan with grounded sources via agentic RAG."""

    role = AgentRole.RESEARCH_STRATEGIST
    artifact_type = ArtifactType.RESEARCH_PLAN

    async def execute(self, project: Any, venue: Any) -> Any:
        """Execute the research strategist pipeline."""
        await self.broadcast_progress(project.id, "Starting research planning...", 5)

        # Build venue context
        venue_ctx = {}
        if venue:
            venue_ctx = {
                "display_name": venue.display_name,
                "venue_type": venue.venue_type,
                "tone_profile": venue.profile_data.tone_profile.model_dump() if venue.profile_data.tone_profile else {},
                "citation_requirements": venue.profile_data.citation_format.model_dump() if venue.profile_data.citation_format else {},
                "rubric_summary": {d.name: d.weight for d in venue.profile_data.quality_rubric.dimensions} if venue.profile_data.quality_rubric else {},
            }

        # Phase 1: Generate research plan
        await self.broadcast_progress(project.id, "Generating research plan...", 15)

        system_prompt = RESEARCH_SYSTEM
        if venue:
            system_prompt += f"\n\nTarget Venue: {venue.display_name} ({venue.venue_type})"
            system_prompt += f"\nVenue Description: {venue.description}"

        user_msg = f"""## Topic
{project.topic_description}

## Author Context
{project.author_context or 'No additional context provided.'}

## Target Venue
{venue.display_name if venue else 'Not specified'}

## Instructions
1. Analyze the topic and identify a specific, defensible contribution claim
2. Plan research queries to find supporting evidence
3. Identify at least 5-10 high-quality sources that support the contribution
4. Map evidence to claims
5. Assess venue alignment
6. Flag any NDA-sensitive areas

Respond with the JSON structure specified in your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=system_prompt,
            project_id=project.id,
            operation="research_plan",
            max_tokens=8192,
            temperature=0.7,
        )

        await self.broadcast_progress(project.id, "Parsing research plan...", 60)

        # Parse the response
        content = result["content"]
        payload = self._parse_research_output(content)

        # Log the contribution claim decision
        self.log_decision(
            project.id,
            decision=f"Selected contribution claim: {payload.get('contribution_claim', 'Unknown')}",
            rationale=payload.get("gap_analysis", ""),
            confidence=0.8,
        )

        # Phase 2: Self-reflection
        await self.broadcast_progress(project.id, "Running self-reflection...", 80)

        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        if not reflection.passed:
            self.logger.warning("[research] Self-reflection failed: %s", reflection.issues_found)

        await self.broadcast_progress(project.id, "Research plan complete", 100)

        # Build metadata
        metadata = ArtifactMetadata(
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cache_read_tokens=result.get("cache_read_tokens", 0),
            cache_write_tokens=result.get("cache_write_tokens", 0),
            duration_ms=result["duration_ms"],
            estimated_cost_usd=result["cost_usd"],
        )

        return self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            target_agent=AgentRole.STRUCTURE_ARCHITECT,
            reflection_result=reflection,
            venue_context=venue_ctx,
        )

    def _parse_research_output(self, content: str) -> dict:
        """Parse the LLM output into structured research plan."""
        try:
            # Find JSON in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback: return raw content as payload
        return {
            "contribution_claim": "Could not parse structured output",
            "raw_content": content,
            "sources": [],
            "evidence_map": {},
        }
