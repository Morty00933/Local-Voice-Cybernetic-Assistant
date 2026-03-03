from __future__ import annotations

import asyncio
import logging
import shlex
from typing import Any

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Whitelisted commands that are safe to run
_ALLOWED_COMMANDS = frozenset({
    # listing / reading
    "ls", "dir", "cat", "head", "tail", "wc",
    # file operations
    "cp", "mv", "rm", "mkdir", "rmdir", "touch", "chmod",
    "ren", "move", "copy", "del", "md",       # Windows equivalents
    "rename", "ln", "basename", "dirname",
    # system info
    "date", "uptime", "whoami", "hostname",
    "df", "free", "top", "ps", "uname",
    # network
    "ping", "curl", "wget",
    # dev tools
    "python", "python3", "pip", "pip3",
    "git", "docker", "kubectl", "node", "npm",
    # shell builtins
    "echo", "pwd", "env", "printenv", "cd", "test",
    "find", "grep", "which", "type", "sort", "uniq", "tr",
})


class SystemCmdTool(BaseTool):
    name = "system_cmd"
    description = "Run a whitelisted shell command on the local machine."

    def __init__(self, timeout: int = 30, allowed: frozenset[str] | None = None):
        self.timeout = timeout
        self.allowed = allowed or _ALLOWED_COMMANDS

    async def execute(self, command: str = "", **kwargs: Any) -> ToolResult:
        if not command.strip():
            return ToolResult(success=False, output="Empty command")

        parts = shlex.split(command)
        base_cmd = parts[0] if parts else ""

        if base_cmd not in self.allowed:
            return ToolResult(
                success=False,
                output=f"Command '{base_cmd}' is not in the whitelist.",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )

            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                return ToolResult(success=True, output=output or "(no output)")
            else:
                return ToolResult(
                    success=False,
                    output=f"Exit code {proc.returncode}\n{err or output}",
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=f"Command timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"system_cmd failed: {e}", exc_info=True)
            return ToolResult(success=False, output=f"Error: {e}")
