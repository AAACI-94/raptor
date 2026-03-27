"""Agent 5: Production Agent.

Takes approved draft sections and produces publish-ready artifacts.
CRITICAL: This agent FORMATS, it does NOT rewrite or summarize.
Draft content is preserved verbatim; only formatting, bibliography, and checklist are generated.
"""

import json
import logging
import re
from typing import Any

from app.agents.base import BaseAgent
from app.models.constants import AgentRole, ArtifactType
from app.models.envelope import ArtifactMetadata
from app.services import artifact_service

logger = logging.getLogger(__name__)

BIBLIOGRAPHY_SYSTEM = """You are a citation formatter. Given a list of research sources and a citation style,
produce a formatted bibliography. Output ONLY valid JSON:
{
  "references": [
    {"number": 1, "formatted": "[1] A. Author, 'Title,' Publication, 2024.", "source_title": "Original title"}
  ]
}

Do NOT add, remove, or modify any sources. Format exactly what is provided."""

CHECKLIST_SYSTEM = """You are a submission checklist generator. Given a document summary and publication target requirements,
generate a submission readiness checklist. Output ONLY valid JSON:
{
  "checklist": [
    {"item": "Check description", "status": "pass|fail|warning", "detail": "Specific detail"}
  ],
  "formatting_notes": "Overall formatting assessment"
}"""


class ProductionAgent(BaseAgent):
    """Produces formatted, publish-ready documents.

    DESIGN: This agent is primarily DETERMINISTIC. Draft content passes through
    verbatim. The LLM is only used for bibliography formatting and checklist generation.
    This prevents the content loss that occurs when asking an LLM to "assemble" a document.
    """

    role = AgentRole.PRODUCTION_AGENT
    artifact_type = ArtifactType.PRODUCTION_OUTPUT

    async def execute(self, project: Any, venue: Any) -> Any:
        await self.broadcast_progress(project.id, "Assembling document...", 10)

        # Get the approved draft and research
        draft = artifact_service.get_latest_artifact(project.id, ArtifactType.SECTION_DRAFT)
        research = artifact_service.get_latest_artifact(project.id, ArtifactType.RESEARCH_PLAN)

        if not draft:
            raise ValueError("No draft found.")

        draft_sections = draft.payload.get("sections", [])
        sources = research.payload.get("sources", []) if research else []
        draft_word_count = draft.payload.get("total_word_count", 0)

        # Step 1: DETERMINISTIC assembly (no LLM, no content loss)
        await self.broadcast_progress(project.id, "Formatting sections...", 20)
        document_sections = []
        all_citations = set()

        for section in draft_sections:
            name = section.get("section_name", "Untitled")
            content = section.get("content", "")

            # Strip confidence flags from final output (they're metadata, not content)
            clean_content = content
            for flag in ["[WELL-SUPPORTED]", "[PARTIALLY-SUPPORTED]", "[AUTHOR-ASSERTION]", "[NDA-FLAG]"]:
                clean_content = clean_content.replace(flag, "")
            clean_content = re.sub(r'\s{2,}', ' ', clean_content).strip()

            document_sections.append({
                "heading": name,
                "content": clean_content,
                "level": 1,
            })

            # Collect cited sources
            for cite in section.get("citations_used", []):
                all_citations.add(cite)

        # Build abstract from first section if it's an abstract/executive summary
        abstract = ""
        if draft_sections:
            first_name = draft_sections[0].get("section_name", "").lower()
            if "abstract" in first_name or "executive summary" in first_name:
                abstract = draft_sections[0].get("content", "")[:1500]
                for flag in ["[WELL-SUPPORTED]", "[PARTIALLY-SUPPORTED]", "[AUTHOR-ASSERTION]", "[NDA-FLAG]"]:
                    abstract = abstract.replace(flag, "")

        # Step 2: LLM for bibliography formatting only
        await self.broadcast_progress(project.id, "Formatting bibliography...", 50)
        references = await self._format_bibliography(project, venue, sources)

        # Step 3: LLM for submission checklist only
        await self.broadcast_progress(project.id, "Generating submission checklist...", 70)
        total_words = sum(len(s["content"].split()) for s in document_sections)
        estimated_pages = max(1, total_words // 350)

        checklist_data = await self._generate_checklist(
            project, venue, total_words, estimated_pages,
            len(document_sections), len(references), draft_word_count,
        )

        # Assemble final payload
        payload = {
            "document": {
                "title": project.title,
                "abstract": abstract,
                "sections": document_sections,
                "references": references,
            },
            "submission_checklist": checklist_data.get("checklist", []),
            "formatting_notes": checklist_data.get("formatting_notes", ""),
            "total_word_count": total_words,
            "estimated_pages": estimated_pages,
            "draft_word_count": draft_word_count,
            "content_preserved": total_words >= draft_word_count * 0.9,  # Sanity check
        }

        self.log_decision(
            project.id,
            decision=f"Produced document: {total_words} words ({estimated_pages} pages), "
                     f"{len(references)} references, {len(document_sections)} sections. "
                     f"Content preservation: {total_words}/{draft_word_count} words "
                     f"({'OK' if payload['content_preserved'] else 'WARNING: content lost'})",
            rationale=checklist_data.get("formatting_notes", ""),
            confidence=0.95,
        )

        if not payload["content_preserved"]:
            logger.warning("[production] Content loss detected: draft had %d words, production has %d",
                          draft_word_count, total_words)

        await self.broadcast_progress(project.id, f"Document complete: {total_words} words", 100)

        # Metadata: combine bibliography + checklist LLM costs
        metadata = ArtifactMetadata(
            model="deterministic+llm",
            input_tokens=0,
            output_tokens=0,
            duration_ms=0,
            estimated_cost_usd=0.0,
        )

        return self.build_envelope(
            project_id=project.id,
            payload=payload,
            metadata=metadata,
            reflection_result=None,  # No reflection needed for deterministic assembly
        )

    async def _format_bibliography(self, project: Any, venue: Any, sources: list) -> list:
        """Use LLM to format sources into publication-appropriate bibliography."""
        if not sources:
            return []

        cite_style = "IEEE numbered"
        if venue and venue.profile_data.citation_format:
            cite_style = f"{venue.profile_data.citation_format.style} ({venue.profile_data.citation_format.format_spec})"

        result = await self.complete(
            messages=[{"role": "user", "content": f"Format these sources as {cite_style} references:\n{json.dumps(sources[:20], indent=2)}"}],
            system=BIBLIOGRAPHY_SYSTEM,
            project_id=project.id,
            operation="format_bibliography",
            max_tokens=4096,
            temperature=0.0,
        )

        try:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                return parsed.get("references", [])
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: create basic references
        return [
            {"number": i+1, "formatted": f"[{i+1}] {s.get('title', 'Untitled')}", "source_title": s.get("title", "")}
            for i, s in enumerate(sources)
        ]

    async def _generate_checklist(self, project: Any, venue: Any,
                                   total_words: int, pages: int,
                                   section_count: int, ref_count: int,
                                   draft_words: int) -> dict:
        """Use LLM to generate publication-specific submission checklist."""
        venue_reqs = ""
        if venue:
            tmpl = venue.profile_data.structural_template
            venue_reqs = f"""Publication Target: {venue.display_name}
Required sections: {len(tmpl.required_sections)}
Page range: {tmpl.total_length_min_pages}-{tmpl.total_length_max_pages} pages
Min references: {venue.profile_data.citation_format.minimum_references}"""

        result = await self.complete(
            messages=[{"role": "user", "content": f"""Document summary:
- Title: {project.title}
- Words: {total_words}
- Pages: ~{pages}
- Sections: {section_count}
- References: {ref_count}
- Draft words preserved: {total_words}/{draft_words}

{venue_reqs or 'General submission'}

Generate a submission readiness checklist."""}],
            system=CHECKLIST_SYSTEM,
            project_id=project.id,
            operation="generate_checklist",
            max_tokens=2048,
            temperature=0.0,
        )

        try:
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

        return {"checklist": [], "formatting_notes": "Could not generate checklist"}
