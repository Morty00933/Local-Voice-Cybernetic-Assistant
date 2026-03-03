"""Tool execution: run tool results as system actions."""
from __future__ import annotations

import asyncio
import logging
import shlex
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Safe commands the executor is allowed to run
_SAFE_COMMANDS = frozenset({
    "xdg-open", "open", "start",  # Open files/URLs
    "notify-send",                 # Desktop notifications
    "pactl", "amixer",            # Volume control
    "xdotool",                     # Window management
    "xclip", "xsel", "pbcopy",   # Clipboard
})


class Executor:
    """Executes tool results as system actions (subprocess, etc.)."""

    def __init__(self, allowed_commands: frozenset[str] | None = None, timeout: int = 15):
        self.allowed = allowed_commands or _SAFE_COMMANDS
        self.timeout = timeout

    async def run_command(self, command: str) -> Dict[str, Any]:
        parts = shlex.split(command)
        if not parts:
            return {"success": False, "error": "Empty command"}

        base = parts[0]
        if base not in self.allowed:
            return {"success": False, "error": f"Command '{base}' not allowed"}

        try:
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Timed out after {self.timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def open_url(self, url: str) -> Dict[str, Any]:
        import sys
        if sys.platform == "win32":
            cmd = f'start "" "{url}"'
        elif sys.platform == "darwin":
            cmd = f'open "{url}"'
        else:
            cmd = f'xdg-open "{url}"'
        return await self.run_command(cmd)

    async def notify(self, title: str, body: str) -> Dict[str, Any]:
        import sys
        if sys.platform == "linux":
            return await self.run_command(f'notify-send "{title}" "{body}"')
        logger.info("Notification: %s — %s", title, body)
        return {"success": True, "stdout": "logged"}
