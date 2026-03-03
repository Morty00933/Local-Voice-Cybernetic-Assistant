"""SSE streaming client for LVCA brain."""
from __future__ import annotations

import json
from typing import Callable

import httpx


def stream_chat(
    text: str,
    base_url: str = "http://localhost:8000",
    session_id: str = "",
    on_token: Callable[[str], None] | None = None,
    on_tool: Callable[[dict], None] | None = None,
    on_done: Callable[[str], None] | None = None,
    on_error: Callable[[str], None] | None = None,
) -> str:
    """Blocking SSE stream consumer. Returns the full response text.

    Raises httpx.HTTPStatusError on non-2xx (allows caller to fallback).
    """
    full_text = ""
    params = {"text": text, "session_id": session_id}

    with httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0), trust_env=False) as client:
        with client.stream("GET", f"{base_url}/api/chat/stream", params=params) as resp:
            resp.raise_for_status()  # raises on 4xx/5xx — caller catches for fallback
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]  # strip "data: "
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                ctype = chunk.get("type", "")

                if ctype == "token":
                    token = chunk.get("text", "")
                    full_text += token
                    if on_token:
                        on_token(token)

                elif ctype == "tool":
                    if on_tool:
                        on_tool(chunk)

                elif ctype == "done":
                    full_text = chunk.get("full_text", full_text)
                    if on_done:
                        on_done(full_text)

                elif ctype == "error":
                    if on_error:
                        on_error(chunk.get("message", "Unknown error"))

    return full_text
