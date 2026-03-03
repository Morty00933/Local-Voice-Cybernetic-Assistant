"""LVCA Orchestrator — FastAPI entry point."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from shared.config import settings
from shared.logging import setup_logging
from .pipeline import Pipeline
from .ws_manager import manager

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="LVCA Orchestrator", version="0.1.0")
pipeline = Pipeline()


# ------------------------------------------------------------------
# REST endpoints
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


class ChatResponse(BaseModel):
    text: str
    session_id: str
    stt_time: float = 0.0
    brain_time: float = 0.0
    tts_time: float = 0.0
    total_time: float = 0.0


@app.get("/api/health")
async def health() -> dict[str, Any]:
    downstream = await pipeline.health_check()
    all_ok = all(downstream.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "services": downstream,
        "active_sessions": manager.active_sessions,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    result = await pipeline.process_text(req.text, session_id=session_id)
    return ChatResponse(
        text=result.text_out,
        session_id=session_id,
        brain_time=result.brain_time,
        tts_time=result.tts_time,
        total_time=result.total_time,
    )


# ------------------------------------------------------------------
# REST voice endpoint
# ------------------------------------------------------------------
@app.post("/api/voice")
async def voice(request: Request):
    """Accept audio WAV, run full pipeline (STT → Brain → TTS), return JSON + audio."""
    audio_bytes = await request.body()
    if not audio_bytes:
        return JSONResponse({"error": "No audio data"}, status_code=400)

    session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
    result = await pipeline.process_audio(audio_bytes, session_id=session_id)

    return JSONResponse({
        "text_in": result.text_in,
        "text_out": result.text_out,
        "stt_time": result.stt_time,
        "brain_time": result.brain_time,
        "tts_time": result.tts_time,
        "total_time": result.total_time,
    })


# ------------------------------------------------------------------
# SSE streaming
# ------------------------------------------------------------------
@app.get("/api/chat/stream")
async def chat_stream(
    text: str = Query(..., description="User message"),
    session_id: str = Query("", description="Session ID"),
):
    """SSE proxy — forwards Brain's streaming response to the client."""
    sid = session_id or str(uuid.uuid4())

    async def proxy():
        async for sse_line in pipeline.process_text_stream(text, session_id=sid):
            yield sse_line

    return StreamingResponse(
        proxy(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ------------------------------------------------------------------
# WebSocket: voice loop
# ------------------------------------------------------------------
@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket) -> None:
    """Full duplex voice: client sends audio chunks, server sends audio + text."""
    session_id = str(uuid.uuid4())
    await manager.connect(ws, session_id)

    try:
        while True:
            data = await ws.receive_bytes()
            if not data:
                continue

            result = await pipeline.process_audio(data, session_id=session_id)

            # Send text response
            await ws.send_json({
                "type": "response",
                "text_in": result.text_in,
                "text_out": result.text_out,
                "stt_time": result.stt_time,
                "brain_time": result.brain_time,
                "tts_time": result.tts_time,
                "total_time": result.total_time,
            })

            # Send audio response
            if result.audio_out:
                await ws.send_bytes(result.audio_out)

    except WebSocketDisconnect:
        logger.info("Voice session ended: %s", session_id)
    except Exception as e:
        logger.error("Voice session error: %s", e, exc_info=True)
    finally:
        manager.disconnect(ws, session_id)


# ------------------------------------------------------------------
# WebSocket: text chat
# ------------------------------------------------------------------
@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    """Text-based chat over WebSocket."""
    session_id = str(uuid.uuid4())
    await manager.connect(ws, session_id)

    try:
        while True:
            msg = await ws.receive_json()
            text = msg.get("text", "")
            if not text.strip():
                continue

            result = await pipeline.process_text(text, session_id=session_id)
            await ws.send_json({
                "type": "response",
                "text": result.text_out,
                "brain_time": result.brain_time,
                "total_time": result.total_time,
            })

    except WebSocketDisconnect:
        logger.info("Chat session ended: %s", session_id)
    except Exception as e:
        logger.error("Chat session error: %s", e, exc_info=True)
    finally:
        manager.disconnect(ws, session_id)
