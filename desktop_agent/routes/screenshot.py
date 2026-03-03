"""Screenshot routes."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import SCREENSHOT_DIR

logger = logging.getLogger(__name__)
router = APIRouter(tags=["screenshot"])


class ScreenshotRequest(BaseModel):
    region: Optional[str] = None  # "x,y,w,h"
    window_title: Optional[str] = None
    resize_width: int = 1280  # Resize for vision model


@router.post("/screenshot")
async def take_screenshot(req: ScreenshotRequest = ScreenshotRequest()):
    import mss
    from PIL import Image

    ts = int(time.time() * 1000)
    filename = f"screenshot_{ts}.png"
    filepath = SCREENSHOT_DIR / filename

    try:
        with mss.mss() as sct:
            if req.region:
                parts = [int(x) for x in req.region.split(",")]
                if len(parts) == 4:
                    monitor = {"left": parts[0], "top": parts[1], "width": parts[2], "height": parts[3]}
                else:
                    monitor = sct.monitors[1]
            elif req.window_title:
                # Try to find window and capture its region
                try:
                    import pygetwindow as gw
                    wins = [w for w in gw.getAllWindows() if req.window_title.lower() in w.title.lower()]
                    if wins:
                        w = wins[0]
                        monitor = {"left": w.left, "top": w.top, "width": w.width, "height": w.height}
                    else:
                        monitor = sct.monitors[1]
                except Exception:
                    monitor = sct.monitors[1]
            else:
                monitor = sct.monitors[1]  # Primary monitor

            img = sct.grab(monitor)
            pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

            # Resize for vision model
            if pil_img.width > req.resize_width:
                ratio = req.resize_width / pil_img.width
                new_h = int(pil_img.height * ratio)
                pil_img = pil_img.resize((req.resize_width, new_h), Image.LANCZOS)

            pil_img.save(str(filepath), "PNG")

        logger.info("Screenshot saved: %s", filepath)
        return {
            "success": True,
            "path": str(filepath),
            "filename": filename,
            "width": pil_img.width,
            "height": pil_img.height,
        }
    except Exception as e:
        logger.error("Screenshot failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}
