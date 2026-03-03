"""REST API client for LVCA orchestrator."""
from __future__ import annotations

import httpx
from typing import Any


class LVCAClient:
    """Synchronous/async REST client for the orchestrator."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(180.0, connect=10.0)

    def chat_sync(self, text: str, session_id: str = "") -> dict[str, Any]:
        """Blocking chat call."""
        with httpx.Client(timeout=self.timeout, trust_env=False) as client:
            resp = client.post(
                f"{self.base_url}/api/chat",
                json={"text": text, "session_id": session_id},
            )
            resp.raise_for_status()
            return resp.json()

    async def chat(self, text: str, session_id: str = "") -> dict[str, Any]:
        """Async chat call."""
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"text": text, "session_id": session_id},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), trust_env=False) as client:
            resp = await client.get(f"{self.base_url}/api/health")
            resp.raise_for_status()
            return resp.json()
