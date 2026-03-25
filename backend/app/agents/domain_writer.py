"""Agent 3: Domain Writer.

Drafts sections INDIVIDUALLY grounded in the research corpus.
Each section gets its own LLM call for full coverage of the outline.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

SECTION_SYSTEM = """Domain Writer for RAPTOR, a multi-agent research authoring platform for cybersecurity.

Your job: Draft ONE section of a paper, grounded in the research corpus.

You must:
1. Write the FULL prose content for this section, hitting the target word count
2. Include inline source attribution (cite by [number] or author depending on venue)
3. Flag confidence levels: [WELL-SUPPORTED], [PARTIALLY-SUPPORTED], [AUTHOR-ASSERTION]
4. Flag any content that may need NDA generalization with [NDA-FLAG]
5. Write substantive content, not summaries. Every paragraph should contain analysis, evidence, or actionable guidance.

CRITICAL: Meet the target word count. If the target is 500-1500 words, write at least 500 words.
Do NOT write a summary or overview. Write the ACTUAL section content as it would appear in the published paper.

Output valid JSON:
{
  "section_name": "Section Title",
  "content": "Full prose content with citations and confidence flags...",
  "word_count": 650,
  "citations_used": ["Source Title 1", "Source Title 2"],
  "confidence_flags": {
    "well_supported": 5,
    "partially_supported": 2,
    "author_assertion": 1
  },
  "nda_flags": ["description of any flagged content"]
}
"""

REFLECTION_PROMPT = """Is every factual claim attributed to a source? Does the tone match
venue expectations? Would a domain expert find any claims unsupported or misleading?
Is the section at least the minimum word count?"""


class DomainWriter(BaseAgent):
    """Drafts each section individually for full outline coverage."""

    role = AgentRole.DOMAIN_WRITER
    artifact_type = ArtifactType.SECTION_DRAFT

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Preparing to draft...", 5)

        # Get upstream artifacts
        outline = artifact_service.get_latest_artifact(project.id, ArtifactType.OUTLINE)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        # Also check for prior review feedback (revision loop)
        prior_review = artifact_service.get_latest_artifact(project.id, ArtifactType.REVIEW)
        revision_guidance = ""
        if prior_review and prior_review.rejection_context:
            revision_guidance = f"""
## REVISION REQUIRED
The Critical Reviewer rejected the previous draft. Address these issues:
Failed criteria: {', '.join(prior_review.rejection_context.failed_criteria)}
Required changes:
{chr(10).join(f'- {c}' for c in prior_review.rejection_context.required_changes)}
"""

        if not outline:
            raise ValueError("No outline found. Run structure stage first.")

        # Build tone and citation context
        tone_instructions = self._build_tone_context(venue)
        cite_fmt = self._build_citation_context(venue)

        # Extract sections from outline
        outline_sections = outline.payload.get("outline", [])
        if not outline_sections:
            raise ValueError("Outline has no sections. Re-run structure stage.")

        sources_json = json.dumps(research.payload.get("sources", []), indent=2)[:4000] if research else "No sources"

        # Draft each section individually
        all_sections = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_duration = 0
        total_cost = 0.0
        prior_sections_summary = ""

        for i, section_spec in enumerate(outline_sections):
            section_name = section_spec.get("section_name", f"Section {i+1}")
            min_words = section_spec.get("min_words", 300)
            max_words = section_spec.get("max_words", 1000)
            criteria = section_spec.get("acceptance_criteria", [])
            assigned_sources = section_spec.get("assigned_sources", [])

            pct = int(10 + (80 * i / len(outline_sections)))
            await self.broadcast_progress(
                project.id,
                f"Drafting section {i+1}/{len(outline_sections)}: {section_name}",
                pct,
            )

            user_msg = f"""## Section to Draft
Name: {section_name}
Target word count: {min_words}-{max_words} words (MINIMUM {min_words} words)
Acceptance criteria:
{chr(10).join(f'- {c}' for c in criteria) if criteria else '- Write substantive content for this section'}

## Assigned Sources
{json.dumps(assigned_sources, indent=2) if assigned_sources else 'Use all available sources'}

## All Research Sources
{sources_json}

## Author Context
{project.author_context or 'None provided'}

## Tone Requirements
{tone_instructions}

## Citation Format
{cite_fmt}

## Prior Sections (for continuity)
{prior_sections_summary or 'This is the first section.'}
{revision_guidance}
## Instructions
Write the COMPLETE content for the "{section_name}" section.
- Hit the target word count ({min_words}-{max_words} words). This is critical.
- Include inline citations [1], [2], etc.
- Flag confidence: [WELL-SUPPORTED], [PARTIALLY-SUPPORTED], [AUTHOR-ASSERTION]
- Flag NDA-sensitive content with [NDA-FLAG]
- Write publication-ready prose, not an outline or summary

Respond with the JSON structure from your system prompt."""

            result = await self.complete(
                messages=[{"role": "user", "content": user_msg}],
                system=SECTION_SYSTEM,
                project_id=project.id,
                operation=f"draft_section_{i+1}",
                max_tokens=8192,
                temperature=0.8,
            )

            section_data = self._parse_section(result["content"], section_name)
            all_sections.append(section_data)

            total_input_tokens += result["input_tokens"]
            total_output_tokens += result["output_tokens"]
            total_duration += result["duration_ms"]
            total_cost += result["cost_usd"]

            # Build summary of prior sections for continuity
            content_preview = section_data.get("content", "")[:200]
            prior_sections_summary += f"\n{section_name}: {content_preview}..."

            logger.info("[writer] Section %d/%d '%s': %d words",
                       i+1, len(outline_sections), section_name,
                       section_data.get("word_count", 0))

        # Assemble payload
        total_words = sum(s.get("word_count", 0) for s in all_sections)
        payload = {
            "sections": all_sections,
            "total_word_count": total_words,
            "section_count": len(all_sections),
            "tone_consistency_notes": f"Drafted {len(all_sections)} sections individually with shared tone context",
        }

        self.log_decision(
            project.id,
            decision=f"Drafted {len(all_sections)} sections, {total_words} total words",
            rationale=f"Each section drafted individually against outline spec. "
                      f"Sections: {', '.join(s.get('section_name','?') for s in all_sections)}",
            confidence=0.8,
        )

        # Single reflection on the combined output
        await self.broadcast_progress(project.id, "Self-reflection on full draft...", 92)
        reflection = await self.self_reflect(
            output=f"Total sections: {len(all_sections)}, Total words: {total_words}. "
                   + json.dumps([{"name": s.get("section_name"), "words": s.get("word_count")} for s in all_sections]),
            reflection_prompt=REFLECTION_PROMPT,
            project_id=project.id,
        )

        await self.broadcast_progress(project.id, f"Draft complete: {total_words} words across {len(all_sections)} sections", 100)

        metadata = ArtifactMetadata(
            model=f"multi-call ({len(all_sections)} sections)",
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            duration_ms=total_duration,
            estimated_cost_usd=total_cost,
        )

        return self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            target_agent=AgentRole.CRITICAL_REVIEWER,
            reflection_result=reflection,
        )

    def _build_tone_context(self, venue: Any) -> str:
        if venue and venue.profile_data.tone_profile:
            tp = venue.profile_data.tone_profile
            return f"Tone: {tp.register}\nPerson: {tp.person}\nVoice: {tp.voice}\nJargon: {tp.jargon_level}"
        return "Default professional tone"

    def _build_citation_context(self, venue: Any) -> str:
        if venue and venue.profile_data.citation_format:
            cf = venue.profile_data.citation_format
            return f"Citation style: {cf.style} ({cf.format_spec}). Minimum {cf.minimum_references} references."
        return "Use numbered inline citations [1], [2], etc."

    def _parse_section(self, content: str, fallback_name: str) -> dict:
        """Parse a single section's JSON output."""
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                if "section_name" not in parsed:
                    parsed["section_name"] = fallback_name
                if "word_count" not in parsed:
                    parsed["word_count"] = len(parsed.get("content", "").split())
                return parsed
        except json.JSONDecodeError:
            pass
        # Fallback: use raw content
        return {
            "section_name": fallback_name,
            "content": content,
            "word_count": len(content.split()),
            "citations_used": [],
            "confidence_flags": {},
            "nda_flags": [],
        }
