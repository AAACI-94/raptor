"""WebSocket connection manager for real-time pipeline events."""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections per project for real-time updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection for a project."""
        await websocket.accept()
        if project_id not in self._connections:
            self._connections[project_id] = []
        self._connections[project_id].append(websocket)
        logger.info("[websocket] Client connected to project %s (%d total)",
                    project_id, len(self._connections[project_id]))

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if project_id in self._connections:
            self._connections[project_id] = [
                ws for ws in self._connections[project_id] if ws != websocket
            ]
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info("[websocket] Client disconnected from project %s", project_id)

    async def broadcast(self, project_id: str, event: dict[str, Any]) -> None:
        """Broadcast an event to all connections watching a project."""
        if project_id not in self._connections:
            return

        message = json.dumps(event)
        dead_connections = []

        for ws in self._connections[project_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(project_id, ws)

    async def send_progress(self, project_id: str, agent: str, message: str, progress_pct: int = 0) -> None:
        """Send a progress update for an agent."""
        await self.broadcast(project_id, {
            "event": "agent_progress",
            "agent": agent,
            "data": {
                "message": message,
                "progress_pct": progress_pct,
            },
        })


# Singleton
ws_manager = WebSocketManager()
