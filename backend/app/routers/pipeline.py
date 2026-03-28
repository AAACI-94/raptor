"""Pipeline control endpoints."""

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.models.pipeline import PipelineStartRequest, PipelineRejectRequest, PipelineOverrideRequest
from app.services.pipeline.orchestrator import orchestrator
from app.services.pipeline.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/projects/{project_id}/pipeline/start")
async def start_pipeline(project_id: str) -> dict:
    """Start the authoring pipeline from topic selection."""
    try:
        result = await orchestrator.start_pipeline(project_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/pipeline/advance")
async def advance_pipeline(project_id: str) -> dict:
    """Advance to the next pipeline stage."""
    try:
        result = await orchestrator.advance_pipeline(project_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/pipeline/reject")
async def reject_pipeline(project_id: str, data: PipelineRejectRequest) -> dict:
    """Reject current stage output and request revision."""
    try:
        result = await orchestrator.reject_stage(project_id, data.feedback, data.target_stage)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/pipeline/override")
async def override_pipeline(project_id: str, data: PipelineOverrideRequest) -> dict:
    """Override rejection and force-advance."""
    try:
        result = await orchestrator.override_stage(project_id, data.reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/pipeline/status")
def get_pipeline_status(project_id: str) -> dict:
    """Get current pipeline state."""
    try:
        status = orchestrator.get_pipeline_status(project_id)
        return status.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket for real-time pipeline events."""
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            # Client can send ping/pong or control messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
