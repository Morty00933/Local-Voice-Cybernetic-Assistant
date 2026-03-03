"""Brain service — FastAPI entry point with SSE streaming and RAG."""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .ollama_client import get_ollama_client, close_ollama_client
from .agent import Agent
from .memory import ConversationMemory
from .embeddings import get_embeddings
from .vectorstore import get_vectorstore
from .retriever import HybridRetriever
from .indexing import Indexer
from .chunking import split_with_metadata
from .tools import (
    SystemCmdTool, FileReadTool, FileWriteTool, FileListTool,
    BrowserTool, CodeGenTool, VisionTool, ALL_DESKTOP_TOOLS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("brain")

# ── Globals ──────────────────────────────────────────────────────
_agent: Agent | None = None
_retriever: HybridRetriever | None = None
_indexer: Indexer | None = None


def _build_retriever() -> HybridRetriever | None:
    try:
        embed = get_embeddings()
        vs = get_vectorstore()
        return HybridRetriever(embed=embed, vs=vs)
    except Exception as e:
        logger.warning("RAG retriever unavailable: %s", e)
        return None


def _get_indexer() -> Indexer | None:
    global _indexer
    if _indexer is None:
        try:
            embed = get_embeddings()
            vs = get_vectorstore()
            _indexer = Indexer(embed=embed, vectorstore=vs)
        except Exception as e:
            logger.warning("RAG indexer unavailable: %s", e)
    return _indexer


def _build_agent() -> Agent:
    global _retriever
    llm = get_ollama_client()
    memory = ConversationMemory()

    core_tools = [
        SystemCmdTool(),
        FileReadTool(),
        FileWriteTool(),
        FileListTool(),
        CodeGenTool(),
        VisionTool(),
    ]

    # Browser needs playwright — optional
    try:
        core_tools.append(BrowserTool())
    except Exception as e:
        logger.warning("BrowserTool unavailable: %s", e)

    all_tools = core_tools + list(ALL_DESKTOP_TOOLS)

    # RAG retriever — optional
    _retriever = _build_retriever()
    if _retriever:
        logger.info("RAG retriever initialized")

    return Agent(llm=llm, tools=all_tools, memory=memory, retriever=_retriever)


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Brain service starting...")
    get_agent()  # pre-init
    logger.info("Brain service ready. Tools: %s", list(get_agent().tools.keys()))
    yield
    logger.info("Brain service shutting down...")
    await close_ollama_client()


app = FastAPI(title="LVCA Brain", version="0.1.0", lifespan=lifespan)


# ── Models ───────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    text: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


class IndexRequest(BaseModel):
    text: str
    filename: str = "manual"
    document_id: int = 0


class IndexResponse(BaseModel):
    chunks_indexed: int
    filename: str


# ── Endpoints ────────────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        agent = get_agent()
        answer = await agent.run(req.text)
        return ChatResponse(response=answer, session_id=req.session_id)
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/stream")
async def chat_stream(
    text: str = Query(..., description="User message"),
    session_id: str = Query("default", description="Session ID"),
):
    """SSE streaming endpoint. Returns Server-Sent Events with token-by-token output."""
    agent = get_agent()

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in agent.run_stream(text):
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/index", response_model=IndexResponse)
async def index_document(req: IndexRequest):
    """Index a text document into the knowledge base."""
    indexer = _get_indexer()
    if not indexer:
        raise HTTPException(status_code=503, detail="RAG indexer not available")

    chunks_meta = split_with_metadata(
        text=req.text,
        filename=req.filename,
        document_id=req.document_id,
    )
    if not chunks_meta:
        return IndexResponse(chunks_indexed=0, filename=req.filename)

    texts = [c["text"] for c in chunks_meta]
    metas = []
    for j, c in enumerate(chunks_meta):
        c["chunk_id"] = f"{req.filename}:{j}"
        metas.append(c)

    n = indexer.upsert_chunks(texts, metas)
    logger.info("Indexed %d chunks from '%s'", n, req.filename)
    return IndexResponse(chunks_indexed=n, filename=req.filename)


@app.get("/health")
async def health():
    ollama_ok = await get_ollama_client().health_check()
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": ollama_ok,
        "tools": list(get_agent().tools.keys()),
        "rag": _retriever is not None,
    }
