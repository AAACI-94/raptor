"""Agent 4: Critical Reviewer (Opus-powered).

Evaluates drafts against venue-specific quality rubrics. Simulates peer review.
"""

import json
import logging
import uuid
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata, RejectionContext
from app.core.database import get_db
from app.services import artifact_service

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM = """Critical Reviewer for RAPTOR, a multi-agent research authoring platform.

Your job: Evaluate paper drafts against venue-specific quality criteria. Simulate peer review.

You use Claude Opus because review quality is where model intelligence pays off most.

For each rubric dimension, provide:
- A score (1-10)
- Specific evidence from the draft supporting the score
- Actionable revision requirements if the score is below the passing threshold

Output valid JSON:
{
  "dimension_scores": [
    {
      "dimension": "practitioner_utility",
      "score": 7,
      "weight": 0.30,
      "min_passing": 7,
      "evidence": "Section 5 provides clear implementation steps with specific tool recommendations",
      "revision_requirements": []
    },
    {
      "dimension": "evidence_quality",
      "score": 5,
      "weight": 0.20,
      "min_passing": 6,
      "evidence": "Section 3 makes ROI claims without cited sources",
      "revision_requirements": [
        "Add empirical data or case study evidence to Section 3",
        "Cite at least 2 additional sources for the ROI claim in paragraph 4"
      ]
    }
  ],
  "aggregate_score": 6.8,
  "passing_threshold": 7.0,
  "recommendation": "revise",
  "structural_feedback": "The argument arc from intro to conclusion is solid but Section 4 needs stronger transitions",
  "reviewer_commentary": "As a senior practitioner reviewing this for [venue], I would say...",
  "revision_priority": [
    "1. Strengthen evidence in Section 3 (evidence_quality below threshold)",
    "2. Add implementation timeline to Section 5 (practitioner_utility borderline)"
  ],
  "target_for_revision": "domain_writer"
}

The recommendation MUST be one of: "accept", "revise", "reject"
"""

REFLECTION_PROMPT = """Have I evaluated every rubric dimension with specific evidence from the draft?
Are my revision requirements actionable and specific? Would a human reviewer at the target venue
reach similar conclusions?"""


class CriticalReviewer(BaseAgent):
    """Evaluates drafts against venue rubrics using Opus for highest reasoning quality."""

    role = AgentRole.CRITICAL_REVIEWER
    artifact_type = ArtifactType.REVIEW

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Starting quality review...", 5)

        # Get the draft
        draft = artifact_service.get_latest_artifact(project.id, ArtifactType.SECTION_DRAFT)
        if not draft:
            raise ValueError("No draft found. Run drafting stage first.")

        # Get research for verification
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        # Build rubric context
        rubric_text = ""
        if venue and venue.profile_data.quality_rubric:
            rubric = venue.profile_data.quality_rubric
            dims = [f"- {d.name} (weight: {d.weight}, min passing: {d.min_passing}): {d.description}"
                    for d in rubric.dimensions]
            rubric_text = f"""Quality Rubric (passing threshold: {rubric.passing_threshold}/10):
{chr(10).join(dims)}"""

        # Build reviewer persona
        persona = ""
        if venue and venue.profile_data.review_simulation_persona:
            rp = venue.profile_data.review_simulation_persona
            persona = f"""Reviewer Persona: {rp.description}
Common feedback patterns: {', '.join(rp.common_feedback_patterns)}"""

        user_msg = f"""## Draft Content
{json.dumps(draft.payload, indent=2)[:8000]}

## Research Plan (for evidence verification)
{json.dumps(research.payload.get('evidence_map', {}), indent=2)[:2000] if research else 'Not available'}

## Quality Rubric
{rubric_text or 'Use general academic quality standards'}

## Reviewer Persona
{persona or 'General reviewer'}

## Instructions
1. Score EVERY dimension in the rubric
2. Provide specific evidence from the draft for each score
3. List actionable revision requirements for dimensions below threshold
4. Give an aggregate weighted score
5. Make a clear recommendation: accept, revise, or reject
6. Write reviewer commentary in the persona's voice
7. If rejecting/revising, specify which agent should handle revisions

Respond with the JSON structure from your system prompt."""

        result = await self.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=REVIEWER_SYSTEM,
            project_id=project.id,
            operation="review",
            max_tokens=8192,
            temperature=0.3,  # Lower temperature for evaluation consistency
        )

        await self.broadcast_progress(project.id, "Parsing review...", 70)
        payload = self._parse_output(result["content"])

        # Store quality scores in DB
        self._store_quality_scores(project.id, draft.artifact_id, payload)

        recommendation = payload.get("recommendation", "revise")
        aggregate = payload.get("aggregate_score", 0)

        self.log_decision(
            project.id,
            decision=f"Review recommendation: {recommendation} (score: {aggregate})",
            rationale=payload.get("structural_feedback", ""),
            confidence=0.9,
        )

        # Self-reflection
        await self.broadcast_progress(project.id, "Self-reflection...", 85)
        reflection = await self.self_reflect(
            output=json.dumps(payload, indent=2)[:3000],
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, "Review complete", 100)

        metadata = ArtifactMetadata(
            model=result["model"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            duration_ms=result["duration_ms"],
            estimated_cost_usd=result["cost_usd"],
        )

        # Build rejection context if not accepted
        rejection = None
        if recommendation != "accept":
            failed = [d["dimension"] for d in payload.get("dimension_scores", [])
                     if d.get("score", 0) < d.get("min_passing", 6)]
            revision_reqs = []
            for d in payload.get("dimension_scores", []):
                revision_reqs.extend(d.get("revision_requirements", []))
            rejection = RejectionContext(
                rejecting_agent=self.role,
                failed_criteria=failed,
                required_changes=revision_reqs[:10],
                target_for_revision=payload.get("target_for_revision", AgentRole.DOMAIN_WRITER),
            )

        quality_scores = {d["dimension"]: d["score"] for d in payload.get("dimension_scores", [])}

        envelope = self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            target_agent=AgentRole.PRODUCTION_AGENT if recommendation == "accept" else None,
            quality_scores=quality_scores,
            reflection_result=reflection,
        )
        envelope.rejection_context = rejection
        if recommendation != "accept":
            envelope.status = "rejected"

        return envelope

    def _store_quality_scores(self, project_id: str, artifact_id: str, payload: dict) -> None:
        """Persist quality scores to the database."""
        try:
            db = get_db()
            for dim in payload.get("dimension_scores", []):
                db.execute(
                    """INSERT INTO quality_scores (id, project_id, artifact_id, dimension,
                       score, reviewer_agent, feedback)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), project_id, artifact_id, dim["dimension"],
                     dim["score"], self.role, dim.get("evidence", "")),
                )
            db.commit()
        except Exception as e:
            logger.warning("[reviewer] Failed to store quality scores: %s", e)

    def _parse_output(self, content: str) -> dict:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        return {"dimension_scores": [], "recommendation": "revise", "raw_content": content}
