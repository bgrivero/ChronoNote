from collections import deque
from datetime import datetime, timezone
from typing import Any
import anyio
from fastapi import WebSocket


class WorkspaceConnectionManager:
    """Manages real-time WebSocket connections and event broadcasting for ChronoNote."""

    def __init__(self, max_history: int = 100):
        self.active_connections: list[WebSocket] = []
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=max_history)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        message = {
            "event": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.recent_events.append(message)

        stale: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)

        for s in stale:
            self.disconnect(s)

        return message

    def emit_from_sync(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Broadcast an event from a synchronous FastAPI route handler."""
        try:
            return anyio.from_thread.run(self.broadcast, event_type, payload)
        except RuntimeError:
            # Fallback if called outside an active AnyIO worker thread
            message = {
                "event": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.recent_events.append(message)
            return message


ws_manager = WorkspaceConnectionManager()
