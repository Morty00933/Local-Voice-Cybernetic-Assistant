from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Directories that are never accessible
_BLOCKED_PATHS = frozenset({
    "/etc/shadow", "/etc/passwd", "/root",
    "C:\\Windows\\System32",
})


def _is_safe_path(path: str) -> bool:
    resolved = str(Path(path).resolve())
    for blocked in _BLOCKED_PATHS:
        if resolved.startswith(blocked):
            return False
    return True


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read contents of a file."

    async def execute(self, path: str = "", max_bytes: int = 100_000, **kwargs: Any) -> ToolResult:
        if not path:
            return ToolResult(success=False, output="No path provided")
        if not _is_safe_path(path):
            return ToolResult(success=False, output="Access denied")

        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"File not found: {path}")
        if not p.is_file():
            return ToolResult(success=False, output=f"Not a file: {path}")

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_bytes:
                content = content[:max_bytes] + f"\n... (truncated at {max_bytes} bytes)"
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output=f"Read error: {e}")


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Write content to a file."

    async def execute(self, path: str = "", content: str = "", **kwargs: Any) -> ToolResult:
        if not path:
            return ToolResult(success=False, output="No path provided")
        if not _is_safe_path(path):
            return ToolResult(success=False, output="Access denied")

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(success=False, output=f"Write error: {e}")


class FileListTool(BaseTool):
    name = "file_list"
    description = "List files and directories at a given path."

    async def execute(self, path: str = ".", **kwargs: Any) -> ToolResult:
        if not _is_safe_path(path):
            return ToolResult(success=False, output="Access denied")

        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"Path not found: {path}")
        if not p.is_dir():
            return ToolResult(success=False, output=f"Not a directory: {path}")

        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            lines = []
            for entry in entries[:200]:
                prefix = "d " if entry.is_dir() else "f "
                size = ""
                if entry.is_file():
                    try:
                        size = f"  ({entry.stat().st_size} bytes)"
                    except OSError:
                        pass
                lines.append(f"{prefix}{entry.name}{size}")
            output = "\n".join(lines) if lines else "(empty directory)"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output=f"List error: {e}")
