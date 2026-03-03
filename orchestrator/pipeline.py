"""Cybernetic loop: Mic → STT → Brain → TTS → Speaker."""
from __future__ import annotations

import io
import logging
import time
import wave
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import httpx
import numpy as np

from shared.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    text_in: str
    text_out: str
    audio_out: Optional[bytes]  # WAV bytes
    stt_time: float
    brain_time: float
    tts_time: float
    total_time: float


class Pipeline:
    """Orchestrates the STT → Brain → TTS pipeline via HTTP calls to microservices."""

    def __init__(self):
        orch_cfg = settings.orchestrator
        self.stt_url = orch_cfg.stt_url
        self.brain_url = orch_cfg.brain_url
        self.tts_url = orch_cfg.tts_url
        self.timeout = httpx.Timeout(180.0, connect=10.0)

    async def process_audio(self, audio_bytes: bytes, session_id: str = "") -> PipelineResult:
        """Full pipeline: audio → text → response text → response audio."""
        t0 = time.time()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. STT: audio → text
            t_stt = time.time()
            stt_resp = await client.post(
                f"{self.stt_url}/api/transcribe",
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"},
            )
            stt_resp.raise_for_status()
            stt_data = stt_resp.json()
            user_text = stt_data.get("text", "")
            stt_time = time.time() - t_stt

            if not user_text.strip():
                return PipelineResult(
                    text_in="", text_out="", audio_out=None,
                    stt_time=stt_time, brain_time=0, tts_time=0,
                    total_time=time.time() - t0,
                )

            # 2. Brain: text → response
            t_brain = time.time()
            brain_resp = await client.post(
                f"{self.brain_url}/api/chat",
                json={"text": user_text, "session_id": session_id},
            )
            brain_resp.raise_for_status()
            brain_data = brain_resp.json()
            reply_text = brain_data.get("response", "")
            brain_time = time.time() - t_brain

            # 3. TTS: response → audio (graceful fallback)
            audio_out = None
            tts_time = 0.0
            try:
                t_tts = time.time()
                tts_resp = await client.post(
                    f"{self.tts_url}/api/synthesize",
                    json={"text": reply_text},
                )
                tts_resp.raise_for_status()
                audio_out = tts_resp.content if tts_resp.headers.get("content-type", "").startswith("audio") else None
                tts_time = time.time() - t_tts
            except Exception as e:
                logger.warning("TTS failed (text-only mode): %s", e)

            return PipelineResult(
                text_in=user_text,
                text_out=reply_text,
                audio_out=audio_out,
                stt_time=stt_time,
                brain_time=brain_time,
                tts_time=tts_time,
                total_time=time.time() - t0,
            )

    async def process_text(self, text: str, session_id: str = "") -> PipelineResult:
        """Text-only pipeline: text → response text → response audio."""
        t0 = time.time()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Brain
            t_brain = time.time()
            brain_resp = await client.post(
                f"{self.brain_url}/api/chat",
                json={"text": text, "session_id": session_id},
            )
            brain_resp.raise_for_status()
            reply_text = brain_resp.json().get("response", "")
            brain_time = time.time() - t_brain

            # TTS (optional — graceful fallback if TTS fails)
            audio_out = None
            tts_time = 0.0
            try:
                t_tts = time.time()
                tts_resp = await client.post(
                    f"{self.tts_url}/api/synthesize",
                    json={"text": reply_text},
                )
                tts_resp.raise_for_status()
                audio_out = tts_resp.content if tts_resp.headers.get("content-type", "").startswith("audio") else None
                tts_time = time.time() - t_tts
            except Exception as e:
                logger.warning("TTS failed (text-only mode): %s", e)

            return PipelineResult(
                text_in=text,
                text_out=reply_text,
                audio_out=audio_out,
                stt_time=0,
                brain_time=brain_time,
                tts_time=tts_time,
                total_time=time.time() - t0,
            )

    async def process_text_stream(self, text: str, session_id: str = "") -> AsyncIterator[str]:
        """Proxy SSE from Brain /api/chat/stream to the client."""
        params = {"text": text, "session_id": session_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "GET",
                f"{self.brain_url}/api/chat/stream",
                params=params,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line + "\n\n"

    async def health_check(self) -> dict[str, Any]:
        """Check health of all downstream services."""
        results = {}
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            for name, url in [("stt", self.stt_url), ("brain", self.brain_url), ("tts", self.tts_url)]:
                try:
                    r = await client.get(f"{url}/health")
                    results[name] = r.status_code == 200
                except Exception:
                    results[name] = False
        return results
