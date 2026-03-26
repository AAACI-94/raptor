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

Your job: Evaluate paper drafts with the rigor of a combined peer reviewer, rhetoric professor,
and investigative editor. You enforce both venue-specific quality criteria AND universal
standards of journalistic verification and logical argumentation.

## STANDARD RUBRIC DIMENSIONS
Score each venue-provided dimension (1-10) with specific evidence.

## JOURNALISTIC VERIFICATION AUDIT (applied to ALL venues)
Check every section for:
1. TWO-SOURCE RULE: Flag any factual claim supported by fewer than 2 independent sources.
   Single-source claims should lower the evidence_quality score.
2. SOURCE TRANSPARENCY: Are sources identified clearly enough for the reader to assess reliability?
   "Studies show..." with no citation is a failure. "According to [Source], who conducted [method]..." is a pass.
3. PRIMARY vs SECONDARY: Is the paper relying too heavily on secondary sources (reports about research)
   rather than primary sources (original data, standards documents, peer-reviewed studies)?
4. CONFLICT OF INTEREST: Does the paper cite vendor research to recommend that vendor's product
   without disclosure? Flag each instance.
5. HEDGING APPROPRIATENESS: Does the paper assert certainty where evidence only suggests?
   "This framework eliminates risk" vs "This framework reduces observed incidents by X% in the studied population."

## LOGICAL RIGOR AUDIT (applied to ALL venues)
Evaluate the logical structure of EVERY causal claim. This is where most security research fails.

### Toulmin Completeness Check
For each major argument, verify:
- CLAIM present? (the assertion)
- DATA present? (cited evidence)
- WARRANT present? (WHY the data supports the claim; the logical bridge)
- QUALIFIER present? (scope limitations)
- REBUTTAL addressed? (strongest counterargument acknowledged)

Score lower on rigor if arguments have claims + data but NO warrant. This is the #1 pattern
in weak security writing: "X happened, therefore Y" without explaining the mechanism.

### Logical Fallacy Detection
Actively scan for and flag these fallacies. Each confirmed fallacy MUST lower the rigor score by 1 point:

CAUSAL FALLACIES:
- Post hoc ergo propter hoc: "After deploying X, incidents dropped 40%." Did X cause it, or did other changes coincide?
- Correlation as causation: "Organizations with X have fewer breaches." Mature orgs adopt X AND other controls.
- Single cause fallacy: Attributing a complex outcome to one factor without qualification.
- Wrong direction: "Successful companies use framework X" does not mean X causes success.

ARGUMENTATIVE FALLACIES:
- Appeal to authority: "[Gartner/Vendor] says X" is not evidence X works. Where is the empirical data?
- Hasty generalization: Small sample (N<10) generalized to the industry without qualification.
- False dichotomy: "Either adopt this or remain vulnerable" ignores alternatives.
- Straw man: Competing approaches represented weakly to make the proposed approach look better.
- Cherry-picking: Only positive results reported; negative findings omitted.
- Survivorship bias: Only successful deployments analyzed; failures ignored.
- Ecological fallacy: Industry statistics applied to individual organizations.
- Circular reasoning: "This framework is effective because it follows best practices, which are the practices in this framework."
- Moving the goalposts: Redefining "success" to match observed outcomes.

### Causal Inference Standards (Mill's Methods)
For any claim of the form "X causes/prevents/reduces Y," check:
1. METHOD OF DIFFERENCE: Was there a comparison group without X? If not, the causal claim is unsubstantiated.
2. CONFOUNDING VARIABLES: What else changed? Were controls in place?
3. MECHANISM: Is the causal pathway explained, or just asserted?
4. DOSE-RESPONSE: If "more X = more Y," does the relationship hold across the range, or only at extremes?
5. TEMPORAL PRECEDENCE: Did X clearly precede Y?
6. ALTERNATIVE EXPLANATIONS: Were other explanations considered and ruled out?

### Argument Arc Evaluation
Check the paper-level argument structure:
- Does the thesis in the introduction match the conclusion?
- Does each section advance the argument, or is any section disconnected?
- Are counterarguments steel-manned (presented in their strongest form) or straw-manned?
- Is the scope consistent throughout? (Don't claim "all organizations" in the intro but study only 3)

## OUTPUT FORMAT
Output valid JSON:
{
  "dimension_scores": [
    {
      "dimension": "dimension_name",
      "score": 7,
      "weight": 0.30,
      "min_passing": 7,
      "evidence": "Specific evidence from the draft",
      "revision_requirements": ["Actionable requirement"]
    }
  ],
  "argumentative_rigor": {
    "toulmin_completeness": "X of Y major claims have complete Toulmin structure",
    "fallacies_detected": [
      {"type": "post_hoc", "location": "Section 3, paragraph 2", "description": "Claims deployment caused improvement without controlling for other changes", "severity": "major"}
    ],
    "causal_claims_audit": [
      {"claim": "Framework reduces incidents by 73%", "has_comparison": true, "has_mechanism": true, "has_confound_analysis": false, "verdict": "partially_valid"}
    ],
    "verification_failures": [
      {"type": "single_source_claim", "location": "Section 2", "claim": "AI agents process 60-80% of routine inquiries", "sources_found": 1, "sources_needed": 2}
    ],
    "argument_arc_coherent": true,
    "counterarguments_addressed": 2,
    "scope_consistent": true
  },
  "aggregate_score": 6.8,
  "passing_threshold": 7.0,
  "recommendation": "revise",
  "structural_feedback": "Overall argument assessment",
  "reviewer_commentary": "As a reviewer at [venue], combining peer review with rhetoric professor scrutiny...",
  "revision_priority": ["1. Most critical fix", "2. Second priority"],
  "target_for_revision": "domain_writer"
}

The recommendation MUST be one of: "accept", "revise", "reject"
A paper with 3+ major logical fallacies MUST be rejected, regardless of other scores.
A paper where more than 30% of factual claims are single-source MUST have evidence_quality capped at 5/10.
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

        # Pre-check: word count and section coverage validation
        draft_sections = draft.payload.get("sections", [])
        total_words = draft.payload.get("total_word_count", sum(s.get("word_count", 0) for s in draft_sections))
        section_count = len(draft_sections)

        structural_warnings = []
        if venue and venue.profile_data.structural_template:
            tmpl = venue.profile_data.structural_template
            required_count = len(tmpl.required_sections)
            if section_count < required_count:
                structural_warnings.append(
                    f"INCOMPLETE: Draft has {section_count} sections but venue requires {required_count}. "
                    f"Missing sections must be written before this paper can pass review."
                )
            min_pages = tmpl.total_length_min_pages or 0
            min_words = min_pages * 350  # ~350 words per page
            if min_words > 0 and total_words < min_words:
                structural_warnings.append(
                    f"UNDERWEIGHT: Draft is {total_words} words but venue requires minimum "
                    f"{min_pages} pages (~{min_words} words). Current draft is {total_words/min_words*100:.0f}% of minimum."
                )

            # Check individual section word counts
            for req_section in tmpl.required_sections:
                matching = [s for s in draft_sections if req_section.name.lower() in s.get("section_name", "").lower()]
                if not matching:
                    structural_warnings.append(f"MISSING SECTION: '{req_section.name}' is required but not present in draft.")
                elif req_section.min_words:
                    actual_words = matching[0].get("word_count", 0)
                    if actual_words < req_section.min_words:
                        structural_warnings.append(
                            f"SHORT SECTION: '{req_section.name}' has {actual_words} words, "
                            f"minimum is {req_section.min_words}."
                        )

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

        # Build structural warnings block
        warnings_block = ""
        if structural_warnings:
            warnings_block = "\n## STRUCTURAL WARNINGS (pre-check failures)\n" + "\n".join(f"- {w}" for w in structural_warnings)
            warnings_block += "\nThese issues MUST be reflected in your completeness and rigor scores. A paper with missing required sections CANNOT pass review."

        # Citation provenance warning
        citation_warning = ""
        if research and research.payload.get("citation_warning"):
            citation_warning = f"\n## CITATION WARNING\n{research.payload['citation_warning']}"

        # Build condensed draft: prose only, no JSON metadata overhead
        # This lets the Reviewer see the FULL paper, not a truncated JSON blob
        condensed_sections = []
        for s in draft_sections:
            name = s.get("section_name", "Untitled")
            content = s.get("content", "")
            word_count = s.get("word_count", len(content.split()))
            citations = s.get("citations_used", [])
            flags = s.get("confidence_flags", {})
            condensed_sections.append(
                f"### {name} ({word_count} words, {len(citations)} citations, "
                f"flags: {flags.get('well_supported', 0)}W/{flags.get('partially_supported', 0)}P/{flags.get('author_assertion', 0)}A)\n\n{content}"
            )
        full_draft_text = "\n\n".join(condensed_sections)

        # Evidence map condensed (just claim -> source title mappings)
        evidence_summary = ""
        if research:
            ev_map = research.payload.get("evidence_map", {})
            if ev_map:
                evidence_lines = [f"- {claim}: {', '.join(sources[:3])}" for claim, sources in list(ev_map.items())[:15]]
                evidence_summary = "\n".join(evidence_lines)

        user_msg = f"""## Draft Content ({total_words} words, {section_count} sections)

{full_draft_text}

## Evidence Map (claim -> supporting sources)
{evidence_summary or 'Not available'}
{citation_warning}
{warnings_block}

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
8. Account for structural warnings in your completeness score

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
