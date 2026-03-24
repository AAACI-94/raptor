"""Export endpoints for generating formatted documents."""

import json
import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.constants import ArtifactType
from app.services import artifact_service, project_service
from app.services.export.docx_export import generate_docx
from app.services.export.markdown_export import generate_markdown

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/export/{format}")
def export_document(project_id: str, format: str):
    """Export the final document in the requested format."""
    # Get production artifact
    artifact = artifact_service.get_latest_artifact(project_id, ArtifactType.PRODUCTION_OUTPUT)
    if not artifact:
        raise HTTPException(status_code=404, detail="No production output found. Complete the pipeline first.")

    project = project_service.get_project(project_id)

    if format == "markdown":
        content = generate_markdown(artifact.payload, project.title)
        return StreamingResponse(
            BytesIO(content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{project.title}.md"'},
        )

    elif format == "docx":
        buffer = generate_docx(artifact.payload, project.title)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{project.title}.docx"'},
        )

    elif format == "json":
        return artifact.payload

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use: markdown, docx, json")


@router.get("/projects/{project_id}/preview")
def preview_document(project_id: str):
    """Return the production output as rendered markdown for in-app preview."""
    # Try production output first, fall back to draft sections
    artifact = artifact_service.get_latest_artifact(project_id, ArtifactType.PRODUCTION_OUTPUT)
    source = "production"

    if not artifact:
        artifact = artifact_service.get_latest_artifact(project_id, ArtifactType.SECTION_DRAFT)
        source = "draft"

    if not artifact:
        # Try to assemble from whatever artifacts exist
        research = artifact_service.get_latest_artifact(project_id, ArtifactType.RESEARCH_PLAN)
        outline = artifact_service.get_latest_artifact(project_id, ArtifactType.OUTLINE)
        if not research and not outline:
            raise HTTPException(status_code=404, detail="No previewable artifacts found.")

        # Build a preview from available artifacts
        project = project_service.get_project(project_id)
        sections = []
        if research:
            claim = research.payload.get("contribution_claim", "")
            sources = research.payload.get("sources", [])
            sections.append({"heading": "Research Plan", "content": f"**Contribution Claim:** {claim}\n\n**Sources found:** {len(sources)}", "level": 1})
            for s in sources[:5]:
                title = s.get("title", "Untitled")
                relevance = s.get("relevance_score", "?")
                sections.append({"heading": title, "content": f"Relevance: {relevance}", "level": 2})
        if outline:
            outline_sections = outline.payload.get("outline", [])
            sections.append({"heading": "Outline", "content": f"{len(outline_sections)} sections planned", "level": 1})
            for o in outline_sections:
                name = o.get("section_name", "Untitled")
                criteria = o.get("acceptance_criteria", [])
                sections.append({"heading": name, "content": "\n".join(f"- {c}" for c in criteria), "level": 2})

        md = generate_markdown({"document": {"sections": sections}}, project.title)
        return {"markdown": md, "source": "partial", "word_count": len(md.split())}

    project = project_service.get_project(project_id)
    payload = artifact.payload

    # For draft artifacts, reshape to match production format
    if source == "draft":
        draft_sections = payload.get("sections", [])
        reshaped = {
            "document": {
                "title": project.title,
                "abstract": "",
                "sections": [
                    {"heading": s.get("section_name", "Untitled"), "content": s.get("content", ""), "level": 1}
                    for s in draft_sections
                ],
                "references": [],
            }
        }
        payload = reshaped

    md = generate_markdown(payload, project.title)
    doc = payload.get("document", {})
    word_count = len(md.split())
    section_count = len(doc.get("sections", []))
    ref_count = len(doc.get("references", []))
    checklist = payload.get("submission_checklist", [])

    return {
        "markdown": md,
        "source": source,
        "word_count": word_count,
        "section_count": section_count,
        "reference_count": ref_count,
        "checklist": checklist,
        "formatting_notes": payload.get("formatting_notes", ""),
    }


@router.get("/projects/{project_id}/figures")
def get_figures(project_id: str):
    """Return all generated figures (Mermaid diagrams) for a project."""
    artifact = artifact_service.get_latest_artifact(project_id, ArtifactType.FIGURES)
    if not artifact:
        raise HTTPException(status_code=404, detail="No figures generated yet. Run the Illustrating stage first.")

    figures = artifact.payload.get("figures", [])
    return {
        "figures": figures,
        "total_figures": len(figures),
        "figure_plan": artifact.payload.get("figure_plan", ""),
        "cross_references": artifact.payload.get("cross_references", []),
        "venue_compliance_notes": artifact.payload.get("venue_compliance_notes", ""),
    }


@router.get("/projects/{project_id}/export/checklist")
def get_submission_checklist(project_id: str):
    """Get the venue submission checklist from the production output."""
    artifact = artifact_service.get_latest_artifact(project_id, ArtifactType.PRODUCTION_OUTPUT)
    if not artifact:
        raise HTTPException(status_code=404, detail="No production output found.")

    return {
        "checklist": artifact.payload.get("submission_checklist", []),
        "formatting_notes": artifact.payload.get("formatting_notes", ""),
    }
