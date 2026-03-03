"""WebSocket TTS streaming server with sentence-level streaming."""
from __future__ import annotations

import asyncio
import io
import logging
import re
import wave
from typing import Any, AsyncIterator, List

import numpy as np
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared.config import settings
from .engine import TTSEngine, create_engine
from .voice_cloning import VoiceManager

logger = logging.getLogger(__name__)

app = FastAPI(title="LVCA TTS Service")

_engine: TTSEngine | None = None
_voice_mgr: VoiceManager | None = None


@app.on_event("startup")
async def startup() -> None:
    global _engine, _voice_mgr
    _engine = create_engine()
    _voice_mgr = VoiceManager()
    logger.info("TTS service started")


@app.on_event("shutdown")
async def shutdown() -> None:
    if _engine:
        _engine.unload()
    logger.info("TTS service stopped")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "engine": type(_engine).__name__ if _engine else "none",
        "voices": _voice_mgr.list_voices() if _voice_mgr else [],
    }


def _audio_to_wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    """Convert float32 audio to WAV bytes."""
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


@app.websocket("/ws/tts")
async def ws_tts(ws: WebSocket) -> None:
    """Streaming TTS: client sends text, server sends WAV audio chunks."""
    await ws.accept()
    logger.info("TTS WebSocket connected")

    try:
        while True:
            msg = await ws.receive_json()
            text = msg.get("text", "")
            voice = msg.get("voice")

            if not text.strip():
                continue

            speaker_wav = None
            if voice and _voice_mgr:
                speaker_wav = _voice_mgr.get_voice_path(voice)
            elif _voice_mgr:
                speaker_wav = _voice_mgr.get_default_voice()

            audio, sr = _engine.synthesize(text, speaker_wav=speaker_wav)
            wav_bytes = _audio_to_wav_bytes(audio, sr)

            await ws.send_bytes(wav_bytes)

    except WebSocketDisconnect:
        logger.info("TTS WebSocket disconnected")
    except Exception as e:
        logger.error("TTS WebSocket error: %s", e, exc_info=True)


class SynthRequest(BaseModel):
    text: str
    voice: str | None = None


@app.post("/api/synthesize")
async def synthesize(req: SynthRequest):
    """REST endpoint: synthesize text and return WAV audio."""
    speaker_wav = None
    if req.voice and _voice_mgr:
        speaker_wav = _voice_mgr.get_voice_path(req.voice)
    elif _voice_mgr:
        speaker_wav = _voice_mgr.get_default_voice()

    audio, sr = _engine.synthesize(req.text, speaker_wav=speaker_wav)
    wav_bytes = _audio_to_wav_bytes(audio, sr)

    from fastapi.responses import Response
    return Response(content=wav_bytes, media_type="audio/wav")


# ── Sentence splitting for streaming TTS ────────────────────────

_SENT_RE = re.compile(r'(?<=[.!?…;])\s+|(?<=\n)\s*')


def _split_sentences(text: str, min_len: int = 10) -> List[str]:
    """Split text into sentences for streaming synthesis.

    Merges very short fragments into the next sentence.
    """
    parts = _SENT_RE.split(text.strip())
    sentences: List[str] = []
    buf = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        buf = (buf + " " + p).strip() if buf else p
        if len(buf) >= min_len:
            sentences.append(buf)
            buf = ""
    if buf:
        if sentences:
            sentences[-1] += " " + buf
        else:
            sentences.append(buf)
    return sentences


@app.post("/api/synthesize/stream")
async def synthesize_stream(req: SynthRequest):
    """Streaming TTS: split into sentences, synthesize each, stream WAV chunks.

    Response is multipart: each chunk is a complete WAV for one sentence.
    Header X-Sentence-Count hints how many chunks to expect.
    """
    speaker_wav = None
    if req.voice and _voice_mgr:
        speaker_wav = _voice_mgr.get_voice_path(req.voice)
    elif _voice_mgr:
        speaker_wav = _voice_mgr.get_default_voice()

    sentences = _split_sentences(req.text)
    if not sentences:
        return StreamingResponse(content=iter([b""]), media_type="audio/wav")

    async def _gen() -> AsyncIterator[bytes]:
        for i, sent in enumerate(sentences):
            try:
                audio, sr = _engine.synthesize(sent, speaker_wav=speaker_wav)
                chunk = _audio_to_wav_bytes(audio, sr)
                # 4-byte length prefix + WAV data (simple framing)
                yield len(chunk).to_bytes(4, "big") + chunk
            except Exception as exc:
                logger.error("Stream TTS error on sentence %d: %s", i, exc)
                continue

    return StreamingResponse(
        _gen(),
        media_type="application/octet-stream",
        headers={
            "X-Sentence-Count": str(len(sentences)),
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/voices")
async def list_voices() -> dict[str, Any]:
    return {"voices": _voice_mgr.list_voices() if _voice_mgr else []}
