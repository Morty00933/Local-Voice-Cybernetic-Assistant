"""WebSocket voice client for LVCA orchestrator.

NOTE: VoiceWSClient is not currently used by the Desktop App
(which uses the REST/SSE path instead). Kept here for future
full-duplex WebSocket voice mode.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import websockets

logger = logging.getLogger(__name__)


class VoiceWSClient:
    """WebSocket client for /ws/voice endpoint."""

    def __init__(
        self,
        url: str = "ws://localhost:8000/ws/voice",
        on_text: Callable[[dict], None] | None = None,
        on_audio: Callable[[bytes], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.url = url
        self.on_text = on_text
        self.on_audio = on_audio
        self.on_error = on_error
        self._ws = None
        self._running = False

    async def connect(self) -> None:
        try:
            self._ws = await websockets.connect(self.url)
            self._running = True
            logger.info("Voice WS connected: %s", self.url)
        except Exception as e:
            logger.error("Voice WS connect failed: %s", e)
            if self.on_error:
                self.on_error(str(e))

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send audio data to the voice endpoint."""
        if self._ws:
            await self._ws.send(audio_bytes)

    async def receive_loop(self) -> None:
        """Receive text (JSON) and audio (bytes) responses."""
        if not self._ws:
            return
        try:
            while self._running:
                msg = await self._ws.recv()
                if isinstance(msg, bytes):
                    # Audio response
                    if self.on_audio:
                        self.on_audio(msg)
                elif isinstance(msg, str):
                    # JSON text response
                    try:
                        data = json.loads(msg)
                        if self.on_text:
                            self.on_text(data)
                    except json.JSONDecodeError:
                        pass
        except websockets.ConnectionClosed:
            logger.info("Voice WS disconnected")
        except Exception as e:
            logger.error("Voice WS error: %s", e)
            if self.on_error:
                self.on_error(str(e))
