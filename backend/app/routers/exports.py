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
