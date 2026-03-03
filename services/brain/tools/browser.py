"""Browser tool: open URLs, search the web via Playwright."""
from __future__ import annotations

import logging
from typing import Any

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class BrowserTool(BaseTool):
    name = "browser"
    description = "Open a URL or search the web. Returns page text content."

    def __init__(self, headless: bool = True, timeout: int = 15000):
        self.headless = headless
        self.timeout = timeout

    async def execute(self, url: str = "", search: str = "", **kwargs: Any) -> ToolResult:
        if not url and not search:
            return ToolResult(success=False, output="Provide 'url' or 'search' argument.")

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ToolResult(success=False, output="playwright is not installed.")

        target = url or f"https://duckduckgo.com/?q={search}"

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                await page.goto(target, timeout=self.timeout, wait_until="domcontentloaded")

                title = await page.title()
                text = await page.inner_text("body")
                # Truncate to reasonable size
                text = text[:5000] if len(text) > 5000 else text

                await browser.close()

                return ToolResult(
                    success=True,
                    output=f"Title: {title}\n\n{text}",
                    data={"url": target, "title": title},
                )

        except Exception as e:
            logger.error("Browser tool error: %s", e, exc_info=True)
            return ToolResult(success=False, output=f"Browser error: {e}")
