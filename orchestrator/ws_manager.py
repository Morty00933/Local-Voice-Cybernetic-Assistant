"""WebSocket connection manager for LVCA sessions."""
from __future__ import annotations

import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> set of WebSocket connections
        self.sessions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, session_id: str) -> None:
        await ws.accept()
        if session_id not in self.sessions:
            self.sessions[session_id] = set()
        self.sessions[session_id].add(ws)
        logger.info("WS connected: session=%s", session_id)

    def disconnect(self, ws: WebSocket, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].discard(ws)
            if not self.sessions[session_id]:
                del self.sessions[session_id]
        logger.info("WS disconnected: session=%s", session_id)

    async def send_json(self, session_id: str, data: dict) -> None:
        if session_id not in self.sessions:
            return
        dead: set[WebSocket] = set()
        for ws in self.sessions[session_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.sessions[session_id].discard(ws)

    async def send_bytes(self, session_id: str, data: bytes) -> None:
        if session_id not in self.sessions:
            return
        dead: set[WebSocket] = set()
        for ws in self.sessions[session_id]:
            try:
                await ws.send_bytes(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.sessions[session_id].discard(ws)

    @property
    def active_sessions(self) -> int:
        return len(self.sessions)


manager = ConnectionManager()
