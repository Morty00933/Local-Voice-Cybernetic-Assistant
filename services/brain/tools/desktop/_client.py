"""HTTP client for Desktop Agent communication."""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DESKTOP_AGENT_URL = os.getenv("DESKTOP_AGENT_URL", "http://host.docker.internal:9100")
TIMEOUT = float(os.getenv("DESKTOP_AGENT_TIMEOUT", "10"))

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=DESKTOP_AGENT_URL,
            timeout=TIMEOUT,
        )
    return _client


async def desktop_get(path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """GET request to Desktop Agent."""
    try:
        resp = await _get_client().get(path, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        logger.error("Desktop Agent unavailable at %s", DESKTOP_AGENT_URL)
        return {"success": False, "error": "Desktop Agent is not running"}
    except Exception as e:
        logger.error("Desktop Agent GET %s failed: %s", path, e)
        return {"success": False, "error": str(e)}


async def desktop_post(path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """POST request to Desktop Agent."""
    try:
        resp = await _get_client().post(path, json=data or {})
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        logger.error("Desktop Agent unavailable at %s", DESKTOP_AGENT_URL)
        return {"success": False, "error": "Desktop Agent is not running"}
    except Exception as e:
        logger.error("Desktop Agent POST %s failed: %s", path, e)
        return {"success": False, "error": str(e)}


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
