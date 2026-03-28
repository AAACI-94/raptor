"""Tests for WebSocket manager."""

from unittest.mock import AsyncMock

from app.services.pipeline.websocket_manager import WebSocketManager


class TestWebSocketManager:
    """Tests for WebSocketManager connection management and broadcasting."""

    async def test_connect_tracks_connection(self):
        """connect should register the websocket for the project."""
        mgr = WebSocketManager()
        ws = AsyncMock()

        await mgr.connect("proj-1", ws)
        assert "proj-1" in mgr._connections
        assert len(mgr._connections["proj-1"]) == 1
        ws.accept.assert_called_once()

    async def test_connect_multiple_clients(self):
        """connect should support multiple clients per project."""
        mgr = WebSocketManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect("proj-1", ws1)
        await mgr.connect("proj-1", ws2)
        assert len(mgr._connections["proj-1"]) == 2

    async def test_disconnect_removes_connection(self):
        """disconnect should remove the specified websocket."""
        mgr = WebSocketManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect("proj-1", ws1)
        await mgr.connect("proj-1", ws2)

        mgr.disconnect("proj-1", ws1)
        assert len(mgr._connections["proj-1"]) == 1
        assert mgr._connections["proj-1"][0] is ws2

    async def test_disconnect_last_client_removes_project(self):
        """disconnect of the last client should remove the project key."""
        mgr = WebSocketManager()
        ws = AsyncMock()

        await mgr.connect("proj-1", ws)
        mgr.disconnect("proj-1", ws)
        assert "proj-1" not in mgr._connections

    async def test_disconnect_nonexistent_is_safe(self):
        """disconnect for a non-tracked project should not raise."""
        mgr = WebSocketManager()
        ws = AsyncMock()
        # Should not raise
        mgr.disconnect("nonexistent", ws)

    async def test_broadcast_sends_to_all(self):
        """broadcast should send the message to all connected clients."""
        mgr = WebSocketManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await mgr.connect("proj-1", ws1)
        await mgr.connect("proj-1", ws2)

        await mgr.broadcast("proj-1", {"event": "test", "data": "hello"})
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    async def test_broadcast_no_clients_is_noop(self):
        """broadcast to a project with no connections should do nothing."""
        mgr = WebSocketManager()
        # Should not raise
        await mgr.broadcast("nonexistent", {"event": "test"})

    async def test_broadcast_cleans_dead_connections(self):
        """broadcast should remove connections that raise on send."""
        mgr = WebSocketManager()
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_text.side_effect = Exception("Connection closed")

        await mgr.connect("proj-1", ws_alive)
        await mgr.connect("proj-1", ws_dead)
        assert len(mgr._connections["proj-1"]) == 2

        await mgr.broadcast("proj-1", {"event": "cleanup"})

        # Dead connection should be removed
        assert len(mgr._connections["proj-1"]) == 1
        assert mgr._connections["proj-1"][0] is ws_alive

    async def test_send_progress_formats_correctly(self):
        """send_progress should broadcast a properly formatted progress event."""
        mgr = WebSocketManager()
        ws = AsyncMock()
        await mgr.connect("proj-1", ws)

        await mgr.send_progress("proj-1", "research_strategist", "Gathering sources", 50)

        ws.send_text.assert_called_once()
        import json
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["event"] == "agent_progress"
        assert sent["agent"] == "research_strategist"
        assert sent["data"]["message"] == "Gathering sources"
        assert sent["data"]["progress_pct"] == 50
