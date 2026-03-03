"""Tool: system information, clipboard, volume, processes, notifications."""
from __future__ import annotations

from typing import Any

from ..base import BaseTool, ToolResult
from ._client import desktop_get, desktop_post


class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Get system information: CPU, RAM, disk, GPU usage."

    async def execute(self, **kwargs: Any) -> ToolResult:
        resp = await desktop_get("/api/system/info")
        if resp.get("success"):
            data = resp
            lines = []
            if "cpu" in data:
                lines.append(f"CPU: {data['cpu'].get('percent', '?')}% ({data['cpu'].get('cores', '?')} cores)")
            if "memory" in data:
                m = data["memory"]
                lines.append(f"RAM: {m.get('used_gb', '?')}/{m.get('total_gb', '?')} GB ({m.get('percent', '?')}%)")
            if "gpu" in data:
                for g in data["gpu"]:
                    lines.append(f"GPU: {g.get('name', '?')} — {g.get('memory_used_mb', '?')}/{g.get('memory_total_mb', '?')} MB")
            return ToolResult(True, "\n".join(lines) or "System info retrieved", data)
        return ToolResult(False, resp.get("error", "Failed to get system info"))


class ClipboardGetTool(BaseTool):
    name = "clipboard_get"
    description = "Get current clipboard text content."

    async def execute(self, **kwargs: Any) -> ToolResult:
        resp = await desktop_get("/api/clipboard")
        if resp.get("success"):
            text = resp.get("text", "")
            preview = text[:200] + "..." if len(text) > 200 else text
            return ToolResult(True, f"Clipboard: {preview}", resp)
        return ToolResult(False, resp.get("error", "Failed to read clipboard"))


class ClipboardSetTool(BaseTool):
    name = "clipboard_set"
    description = "Set clipboard text content. Args: text (str) — text to copy."

    async def execute(self, **kwargs: Any) -> ToolResult:
        text = kwargs.get("text", "")
        if not text:
            return ToolResult(False, "Missing required argument: text")
        resp = await desktop_post("/api/clipboard", {"text": text})
        if resp.get("success"):
            return ToolResult(True, f"Copied {resp.get('chars', len(text))} chars to clipboard", resp)
        return ToolResult(False, resp.get("error", "Failed to set clipboard"))


class VolumeControlTool(BaseTool):
    name = "volume_control"
    description = (
        "Get or set system volume. Args: level (int, optional) — 0-100; "
        "mute (bool, optional) — mute/unmute. No args = get current."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        if not kwargs or (not kwargs.get("level") and kwargs.get("mute") is None):
            # GET current volume
            resp = await desktop_get("/api/media/volume")
        else:
            payload = {}
            if "level" in kwargs:
                payload["level"] = int(kwargs["level"])
            if "mute" in kwargs:
                payload["mute"] = bool(kwargs["mute"])
            resp = await desktop_post("/api/media/volume", payload)

        if resp.get("success"):
            lvl = resp.get("level", "?")
            muted = " (MUTED)" if resp.get("muted") else ""
            return ToolResult(True, f"Volume: {lvl}%{muted}", resp)
        return ToolResult(False, resp.get("error", "Failed volume control"))


class MediaControlTool(BaseTool):
    name = "media_control"
    description = (
        "Control media playback. Args: action (str) — one of: "
        "play_pause, next, prev, stop."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "play_pause")
        valid = {"play_pause", "next", "prev", "stop"}
        if action not in valid:
            return ToolResult(False, f"Invalid action. Choose from: {', '.join(valid)}")
        resp = await desktop_post(f"/api/media/{action}")
        if resp.get("success"):
            return ToolResult(True, f"Media: {action}", resp)
        return ToolResult(False, resp.get("error", f"Failed: {action}"))


class ProcessListTool(BaseTool):
    name = "process_list"
    description = (
        "List running processes sorted by resource usage. "
        "Args: top (int, optional) — number of results (default 30); "
        "sort_by (str, optional) — 'memory' or 'cpu'."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        params = {}
        if "top" in kwargs:
            params["top"] = int(kwargs["top"])
        if "sort_by" in kwargs:
            params["sort_by"] = kwargs["sort_by"]
        resp = await desktop_get("/api/process/list", params)
        if resp.get("success"):
            procs = resp.get("processes", [])
            lines = [f"  {p['name']} (PID {p['pid']}) — CPU {p['cpu_percent']}%, RAM {p['memory_mb']}MB"
                     for p in procs[:10]]
            summary = f"Top processes ({resp.get('total', '?')} total):\n" + "\n".join(lines)
            return ToolResult(True, summary, resp)
        return ToolResult(False, resp.get("error", "Failed to list processes"))


class ProcessKillTool(BaseTool):
    name = "process_kill"
    description = (
        "Kill a process. Args: name (str, optional) — process name; "
        "pid (int, optional) — process ID."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        name = kwargs.get("name")
        pid = kwargs.get("pid")
        if not name and not pid:
            return ToolResult(False, "Provide 'name' or 'pid'")
        payload = {}
        if name:
            payload["name"] = name
        if pid:
            payload["pid"] = int(pid)
        resp = await desktop_post("/api/process/kill", payload)
        if resp.get("success"):
            killed = resp.get("killed", [])
            return ToolResult(True, f"Killed: {killed}", resp)
        return ToolResult(False, resp.get("error", "Failed to kill process"))


class NotifyTool(BaseTool):
    name = "notify"
    description = (
        "Send a desktop notification. Args: message (str) — notification text; "
        "title (str, optional) — title (default 'LVCA')."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        message = kwargs.get("message", "")
        if not message:
            return ToolResult(False, "Missing required argument: message")
        payload = {"message": message}
        if "title" in kwargs:
            payload["title"] = kwargs["title"]
        resp = await desktop_post("/api/notify", payload)
        if resp.get("success"):
            return ToolResult(True, f"Notification sent: {payload.get('title', 'LVCA')}", resp)
        return ToolResult(False, resp.get("error", "Failed to send notification"))
