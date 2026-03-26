"""Agent 3: Domain Writer.

Drafts sections INDIVIDUALLY grounded in the research corpus.
Each section gets its own LLM call for full coverage of the outline.
"""

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.core.database import get_db
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

        all_sources = research.payload.get("sources", []) if research else []

        # Build a source lookup by title for efficient filtering
        source_by_title = {}
        for s in all_sources:
            title = s.get("title", "").lower().strip()
            source_by_title[title] = s

        # Load learned prompt patterns for this venue (cross-project learning)
        learned_guidance = self._get_learned_patterns(venue)

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
            assigned_source_titles = section_spec.get("assigned_sources", [])

            # Filter sources: only send assigned sources for this section
            # Falls back to all sources if no assignments or no matches
            section_sources = []
            if assigned_source_titles:
                for title in assigned_source_titles:
                    match = source_by_title.get(title.lower().strip())
                    if match:
                        section_sources.append(match)
                    else:
                        # Fuzzy match: check if any source title contains this string
                        for st, s in source_by_title.items():
                            if title.lower() in st or st in title.lower():
                                section_sources.append(s)
                                break

            # If no matches found, send top 3 most relevant sources
            if not section_sources:
                section_sources = sorted(
                    all_sources,
                    key=lambda s: s.get("relevance_score", 0),
                    reverse=True,
                )[:3]

            # Condense sources: title + key findings only (not full metadata)
            condensed_sources = []
            for idx, s in enumerate(section_sources):
                condensed_sources.append(
                    f"[{idx+1}] {s.get('title', 'Untitled')}\n"
                    f"    Type: {s.get('source_type', '?')} | "
                    f"Relevance: {s.get('relevance_score', '?')}\n"
                    f"    Key findings: {s.get('key_findings', s.get('content_summary', 'N/A'))}"
                )
            sources_text = "\n".join(condensed_sources) if condensed_sources else "No specific sources assigned."

            pct = int(10 + (80 * i / len(outline_sections)))
            await self.broadcast_progress(
                project.id,
                f"Drafting section {i+1}/{len(outline_sections)}: {section_name} ({len(section_sources)} sources)",
                pct,
            )

            user_msg = f"""## Section to Draft
Name: {section_name}
Target word count: {min_words}-{max_words} words (MINIMUM {min_words} words)
Acceptance criteria:
{chr(10).join(f'- {c}' for c in criteria) if criteria else '- Write substantive content for this section'}

## Sources for This Section ({len(section_sources)} assigned)
{sources_text}

## Author Context
{project.author_context or 'None provided'}

## Tone Requirements
{tone_instructions}

## Citation Format
{cite_fmt}

## Prior Sections (for continuity)
{prior_sections_summary or 'This is the first section.'}
{revision_guidance}{learned_guidance}
## Instructions
Write the COMPLETE content for the "{section_name}" section.
- Hit the target word count ({min_words}-{max_words} words). This is critical.
- Include inline citations [1], [2], etc. referencing the sources above.
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

    def _get_learned_patterns(self, venue: Any) -> str:
        """Extract recurring revision requirements from past reviews for this venue.

        Cross-project learning: if the Reviewer consistently asks for the same thing
        (e.g., "add confidence intervals"), inject that as a permanent instruction
        so future drafts avoid the same mistakes.
        """
        if not venue:
            return ""

        try:
            db = get_db()
            # Find revision requirements from past reviews for this venue type
            rows = db.execute(
                """SELECT a.envelope FROM artifacts a
                   JOIN projects p ON a.project_id = p.id
                   WHERE a.artifact_type = 'review'
                   AND a.status = 'rejected'
                   AND p.venue_profile_id = ?
                   ORDER BY a.created_at DESC LIMIT 10""",
                (venue.id,),
            ).fetchall()

            if not rows:
                return ""

            # Extract revision requirements from past reviews
            requirement_counts: dict[str, int] = {}
            for row in rows:
                import json as _json
                try:
                    envelope = _json.loads(row["envelope"])
                    payload = envelope.get("payload", {})
                    for dim in payload.get("dimension_scores", []):
                        for req in dim.get("revision_requirements", []):
                            # Normalize: lowercase, strip specific references
                            normalized = req.lower().strip()
                            # Group similar patterns
                            for pattern_key in [
                                "confidence interval", "sample size", "methodology",
                                "empirical data", "case study", "worked example",
                                "implementation detail", "before/after", "metrics",
                                "reproducible", "tool", "command", "step-by-step",
                                "formal definition", "threat model", "evaluation",
                            ]:
                                if pattern_key in normalized:
                                    requirement_counts[pattern_key] = requirement_counts.get(pattern_key, 0) + 1
                                    break
                except Exception:
                    continue

            # Only surface patterns that appear in 2+ reviews (consistent feedback)
            recurring = [(pattern, count) for pattern, count in requirement_counts.items() if count >= 2]
            if not recurring:
                return ""

            recurring.sort(key=lambda x: -x[1])
            patterns = [f"- Include {p} (requested in {c} prior reviews)" for p, c in recurring[:5]]

            return f"""
## Learned Quality Patterns for {venue.display_name}
Based on {len(rows)} past reviews, these elements are consistently requested:
{chr(10).join(patterns)}
Address these proactively in your draft to avoid revision cycles.
"""
        except Exception as e:
            self.logger.warning("[writer] Failed to load learned patterns: %s", e)
            return ""

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
