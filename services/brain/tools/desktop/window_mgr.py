"""Tool: window management — list, focus, minimize, maximize, etc."""
from __future__ import annotations

from typing import Any

from ..base import BaseTool, ToolResult
from ._client import desktop_get, desktop_post


class WindowListTool(BaseTool):
    name = "window_list"
    description = "List all open windows with their titles."

    async def execute(self, **kwargs: Any) -> ToolResult:
        resp = await desktop_get("/api/windows")
        if resp.get("success"):
            windows = resp.get("windows", [])
            if not windows:
                return ToolResult(True, "No open windows found", resp)
            lines = [f"  - {w['title']}" for w in windows if w.get("title")]
            return ToolResult(True, f"Open windows:\n" + "\n".join(lines), resp)
        return ToolResult(False, resp.get("error", "Failed to list windows"))


class WindowControlTool(BaseTool):
    name = "window_control"
    description = (
        "Control a window. Args: title (str) — window title (partial match); "
        "action (str) — one of: focus, minimize, maximize, restore, close; "
        "width/height (int, optional) — for resize; x/y (int, optional) — for move."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        title = kwargs.get("title", "")
        action = kwargs.get("action", "focus")
        if not title:
            return ToolResult(False, "Missing required argument: title")

        endpoint = f"/api/windows/{action}"
        payload: dict[str, Any] = {"title": title}

        # Add optional size/position params
        if action == "resize":
            if "width" in kwargs:
                payload["width"] = int(kwargs["width"])
            if "height" in kwargs:
                payload["height"] = int(kwargs["height"])
        elif action == "move":
            if "x" in kwargs:
                payload["x"] = int(kwargs["x"])
            if "y" in kwargs:
                payload["y"] = int(kwargs["y"])

        resp = await desktop_post(endpoint, payload)
        if resp.get("success"):
            return ToolResult(True, f"Window '{title}': {action} done", resp)
        return ToolResult(False, resp.get("error", f"Failed to {action} window"))
