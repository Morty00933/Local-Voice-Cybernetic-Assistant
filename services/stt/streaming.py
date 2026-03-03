"""WebSocket STT streaming server."""
from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Any

import numpy as np
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from shared.config import settings
from .engine import TranscriptionEngine
from .preprocessor import AudioPreprocessor
from .vad import VoiceActivityDetector

logger = logging.getLogger(__name__)

app = FastAPI(title="LVCA STT Service")

_engine: TranscriptionEngine | None = None
_preprocessor: AudioPreprocessor | None = None


@app.on_event("startup")
async def startup() -> None:
    global _engine, _preprocessor
    _engine = TranscriptionEngine()
    _engine.load_model()
    _preprocessor = AudioPreprocessor()
    logger.info("STT service started")


@app.on_event("shutdown")
async def shutdown() -> None:
    if _engine:
        _engine.unload_model()
    logger.info("STT service stopped")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": _engine.model_size if _engine else "not loaded",
        "device": _engine.device if _engine else "unknown",
    }


@app.websocket("/ws/stt")
async def ws_stt(ws: WebSocket) -> None:
    """Streaming STT: client sends raw PCM int16 chunks, server sends back text."""
    await ws.accept()
    logger.info("STT WebSocket connected")

    vad = VoiceActivityDetector(
        threshold=0.5,
        min_speech_ms=300,
        min_silence_ms=500,
    )

    try:
        while True:
            data = await ws.receive_bytes()
            if not data:
                continue

            chunk = _preprocessor.load_buffer(data)
            chunk = _preprocessor.preprocess_buffer(chunk)
            speech = vad.process_chunk(chunk)

            if speech is not None:
                result = _engine.transcribe_buffer(speech)
                if result.text.strip():
                    await ws.send_json({
                        "type": "transcription",
                        "text": result.text,
                        "language": result.language,
                        "duration": result.duration,
                        "processing_time": result.processing_time,
                    })

    except WebSocketDisconnect:
        logger.info("STT WebSocket disconnected")
    except Exception as e:
        logger.error("STT WebSocket error: %s", e, exc_info=True)
    finally:
        # Flush remaining audio
        remaining = vad.finalize()
        if remaining is not None and _engine:
            result = _engine.transcribe_buffer(remaining)
            if result.text.strip():
                try:
                    await ws.send_json({
                        "type": "transcription",
                        "text": result.text,
                        "final": True,
                    })
                except Exception:
                    pass


@app.post("/api/transcribe")
async def transcribe(request: Request, language: str | None = None) -> dict[str, Any]:
    """Transcribe audio from request body (WAV/PCM bytes) or file path.

    Accepts:
      - audio/wav body  → parse WAV, extract PCM, transcribe in-memory
      - application/octet-stream → treat as raw PCM int16 16kHz mono
      - text/plain or query ?audio_path= → file-path mode (legacy)
    """
    content_type = (request.headers.get("content-type") or "").lower()
    body = await request.body()

    # ── WAV / raw audio bytes ──────────────────────────────────
    if body and content_type in ("audio/wav", "audio/x-wav", "audio/wave",
                                  "application/octet-stream"):
        if body[:4] == b"RIFF":
            # Parse WAV container → extract raw PCM
            try:
                with wave.open(io.BytesIO(body), "rb") as wf:
                    sr = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            except Exception as exc:
                return {"text": "", "error": f"WAV parse failed: {exc}"}
        else:
            # Raw PCM int16 bytes
            audio = np.frombuffer(body, dtype=np.int16).astype(np.float32) / 32768.0

        audio = _preprocessor.preprocess_buffer(audio)
        result = _engine.transcribe_buffer(audio, language=language)
        return {
            "text": result.text,
            "language": result.language,
            "language_probability": result.language_probability,
            "duration": result.duration,
            "processing_time": result.processing_time,
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text}
                for s in result.segments
            ],
        }

    # ── Legacy file-path mode ──────────────────────────────────
    audio_path = request.query_params.get("audio_path", "")
    if not audio_path and body:
        audio_path = body.decode("utf-8", errors="ignore").strip()
    if not audio_path:
        return {"text": "", "error": "No audio data or audio_path provided"}

    preprocessed = _preprocessor.preprocess(audio_path)
    result = _engine.transcribe(preprocessed, language=language)
    return {
        "text": result.text,
        "language": result.language,
        "language_probability": result.language_probability,
        "duration": result.duration,
        "processing_time": result.processing_time,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in result.segments
        ],
    }
