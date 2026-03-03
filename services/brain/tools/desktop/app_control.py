"""Tool: launch and close applications."""
from __future__ import annotations

from typing import Any

from ..base import BaseTool, ToolResult
from ._client import desktop_post, desktop_get


class AppLaunchTool(BaseTool):
    name = "app_launch"
    description = (
        "Launch an application. Args: app (str) — name like 'chrome', 'vscode', "
        "'terminal', 'explorer'; args (str, optional) — command line arguments."
    )

    async def execute(self, **kwargs: Any) -> ToolResult:
        app = kwargs.get("app", "")
        if not app:
            return ToolResult(False, "Missing required argument: app")
        payload = {"app": app}
        if kwargs.get("args"):
            payload["args"] = kwargs["args"]
        resp = await desktop_post("/api/app/launch", payload)
        if resp.get("success"):
            return ToolResult(True, f"Launched {app}", resp)
        return ToolResult(False, resp.get("error", "Failed to launch app"))


class AppCloseTool(BaseTool):
    name = "app_close"
    description = (
        "Close a running application. Args: name (str, optional) — process name; "
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
        resp = await desktop_post("/api/app/close", payload)
        if resp.get("success"):
            closed = resp.get("closed", [])
            return ToolResult(True, f"Closed: {', '.join(closed)}", resp)
        return ToolResult(False, resp.get("error", "Failed to close app"))


class AppListTool(BaseTool):
    name = "app_list"
    description = "List all known application names that can be launched."

    async def execute(self, **kwargs: Any) -> ToolResult:
        resp = await desktop_get("/api/app/list")
        apps = resp.get("apps", [])
        return ToolResult(True, f"Available apps: {', '.join(apps)}", resp)
