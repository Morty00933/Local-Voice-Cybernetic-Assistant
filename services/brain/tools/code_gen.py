"""Code generation and execution tool."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Allowed languages and their interpreters
_INTERPRETERS = {
    "python": "python3",
    "bash": "bash",
    "sh": "sh",
}


class CodeGenTool(BaseTool):
    name = "code_gen"
    description = "Execute a code snippet in Python or Bash. Returns stdout/stderr."

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def execute(
        self, code: str = "", language: str = "python", **kwargs: Any
    ) -> ToolResult:
        if not code.strip():
            return ToolResult(success=False, output="No code provided.")

        lang = language.lower()
        interpreter = _INTERPRETERS.get(lang)
        if not interpreter:
            return ToolResult(
                success=False,
                output=f"Unsupported language: {lang}. Supported: {list(_INTERPRETERS.keys())}",
            )

        suffix = ".py" if lang == "python" else ".sh"
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                script_path = f.name

            proc = await asyncio.create_subprocess_exec(
                interpreter, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)

            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            # Cleanup
            Path(script_path).unlink(missing_ok=True)

            if proc.returncode == 0:
                return ToolResult(success=True, output=out or "(no output)")
            else:
                return ToolResult(
                    success=False,
                    output=f"Exit code {proc.returncode}\nstdout:\n{out}\nstderr:\n{err}",
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output=f"Code execution timed out after {self.timeout}s")
        except Exception as e:
            logger.error("code_gen error: %s", e, exc_info=True)
            return ToolResult(success=False, output=f"Execution error: {e}")
