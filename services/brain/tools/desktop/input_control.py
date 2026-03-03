"""Tool: keyboard and mouse input simulation."""
from __future__ import annotations

from typing import Any

from ..base import BaseTool, ToolResult
from ._client import desktop_post, desktop_get


class TypeTextTool(BaseTool):
    name = "type_text"
    description = (
        "Type text on the keyboard. Args: text (str) — text to type; "
        "interval (float, optional) — delay between keys in seconds (default 0.02)."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        text = kwargs.get("text", "")
        if not text:
            return ToolResult(False, "Missing required argument: text")
        payload = {"text": text}
        if "interval" in kwargs:
            payload["interval"] = float(kwargs["interval"])
        resp = await desktop_post("/api/input/type", payload)
        if resp.get("success"):
            return ToolResult(True, f"Typed {resp.get('chars', len(text))} characters", resp)
        return ToolResult(False, resp.get("error", "Failed to type text"))


class HotkeyTool(BaseTool):
    name = "hotkey"
    description = (
        "Press a keyboard shortcut. Args: keys (list[str]) — keys to press, "
        "e.g. ['ctrl', 's'] for save, ['alt', 'tab'] for switch window."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        keys = kwargs.get("keys", [])
        if not keys:
            return ToolResult(False, "Missing required argument: keys")
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split("+")]
        resp = await desktop_post("/api/input/hotkey", {"keys": keys})
        if resp.get("success"):
            return ToolResult(True, f"Pressed {resp.get('keys', '+'.join(keys))}", resp)
        return ToolResult(False, resp.get("error", "Failed to press hotkey"))


class MouseClickTool(BaseTool):
    name = "click"
    description = (
        "Click the mouse at screen coordinates. Args: x (int), y (int) — position; "
        "button (str, optional) — 'left'/'right'/'middle'; clicks (int, optional) — count."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        x = kwargs.get("x")
        y = kwargs.get("y")
        if x is None or y is None:
            return ToolResult(False, "Missing required arguments: x, y")
        payload = {"x": int(x), "y": int(y)}
        if "button" in kwargs:
            payload["button"] = kwargs["button"]
        if "clicks" in kwargs:
            payload["clicks"] = int(kwargs["clicks"])
        resp = await desktop_post("/api/input/click", payload)
        if resp.get("success"):
            return ToolResult(True, f"Clicked at ({x}, {y})", resp)
        return ToolResult(False, resp.get("error", "Failed to click"))


class ScrollTool(BaseTool):
    name = "scroll"
    description = (
        "Scroll the mouse wheel. Args: clicks (int) — positive=up, negative=down; "
        "x/y (int, optional) — position to scroll at."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        clicks = kwargs.get("clicks")
        if clicks is None:
            return ToolResult(False, "Missing required argument: clicks")
        payload = {"clicks": int(clicks)}
        if "x" in kwargs:
            payload["x"] = int(kwargs["x"])
        if "y" in kwargs:
            payload["y"] = int(kwargs["y"])
        resp = await desktop_post("/api/input/scroll", payload)
        if resp.get("success"):
            return ToolResult(True, f"Scrolled {'up' if int(clicks) > 0 else 'down'}", resp)
        return ToolResult(False, resp.get("error", "Failed to scroll"))
