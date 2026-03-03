"""Vision tool: describe images or screenshots using Ollama multimodal."""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult
from shared.config import settings

logger = logging.getLogger(__name__)


class VisionTool(BaseTool):
    name = "vision"
    description = "Describe an image file or screenshot using a vision model."

    def __init__(self, ollama_base_url: str | None = None, model: str = "llava"):
        # Default to shared config so the URL is always consistent
        if ollama_base_url is None:
            ollama_base_url = settings.ollama.base_url
        self.ollama_url = ollama_base_url
        self.model = model

    async def execute(self, image_path: str = "", prompt: str = "Describe this image.", **kwargs: Any) -> ToolResult:
        if not image_path:
            return ToolResult(success=False, output="No image_path provided.")

        p = Path(image_path)
        if not p.exists():
            return ToolResult(success=False, output=f"File not found: {image_path}")

        try:
            import httpx
            image_data = base64.b64encode(p.read_bytes()).decode("ascii")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                resp.raise_for_status()
                text = resp.json().get("response", "")

            return ToolResult(
                success=True,
                output=text,
                data={"image_path": image_path, "model": self.model},
            )

        except Exception as e:
            logger.error("Vision tool error: %s", e, exc_info=True)
            return ToolResult(success=False, output=f"Vision error: {e}")
