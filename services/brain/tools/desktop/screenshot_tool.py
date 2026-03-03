"""Tool: take screenshots for vision analysis."""
from __future__ import annotations

from typing import Any

from ..base import BaseTool, ToolResult
from ._client import desktop_post


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = (
        "Take a screenshot of the screen. Returns the file path to the saved image. "
        "Use the 'vision' tool afterwards to analyze the screenshot content. "
        "Args: monitor (int, optional) — monitor number (default 0 = primary)."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        payload = {}
        if "monitor" in kwargs:
            payload["monitor"] = int(kwargs["monitor"])
        resp = await desktop_post("/api/screenshot", payload)
        if resp.get("success"):
            path = resp.get("path", "")
            return ToolResult(
                True,
                f"Screenshot saved: {path}. Use the 'vision' tool to analyze it.",
                resp,
            )
        return ToolResult(False, resp.get("error", "Failed to take screenshot"))
