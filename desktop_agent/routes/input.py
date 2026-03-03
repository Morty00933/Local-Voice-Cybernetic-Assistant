"""Keyboard and mouse input routes."""
from __future__ import annotations

import logging
from typing import Optional

import pyautogui
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import MAX_TYPE_LENGTH

logger = logging.getLogger(__name__)
router = APIRouter(tags=["input"])


# ── Request models ───────────────────────────────────────────────

class TypeTextRequest(BaseModel):
    text: str
    interval: float = 0.02


class HotkeyRequest(BaseModel):
    keys: list[str]  # e.g. ["ctrl", "s"]


class ClickRequest(BaseModel):
    x: int
    y: int
    button: str = "left"  # left | right | middle
    clicks: int = 1


class MoveRequest(BaseModel):
    x: int
    y: int
    duration: float = 0.3


class ScrollRequest(BaseModel):
    clicks: int  # positive = up, negative = down
    x: Optional[int] = None
    y: Optional[int] = None


class DragRequest(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration: float = 0.5
    button: str = "left"


# ── Keyboard ─────────────────────────────────────────────────────

@router.post("/input/type")
async def type_text(req: TypeTextRequest):
    if len(req.text) > MAX_TYPE_LENGTH:
        return {
            "success": False,
            "error": f"Text too long ({len(req.text)} > {MAX_TYPE_LENGTH})",
        }
    try:
        pyautogui.typewrite(req.text, interval=req.interval) \
            if req.text.isascii() \
            else pyautogui.write(req.text)
        logger.info("Typed %d chars", len(req.text))
        return {"success": True, "chars": len(req.text)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/input/hotkey")
async def hotkey(req: HotkeyRequest):
    try:
        pyautogui.hotkey(*req.keys)
        combo = "+".join(req.keys)
        logger.info("Hotkey: %s", combo)
        return {"success": True, "keys": combo}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/input/press")
async def press_key(key: str):
    """Press and release a single key."""
    try:
        pyautogui.press(key)
        logger.info("Pressed: %s", key)
        return {"success": True, "key": key}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Mouse ────────────────────────────────────────────────────────

@router.post("/input/click")
async def click(req: ClickRequest):
    try:
        pyautogui.click(req.x, req.y, clicks=req.clicks, button=req.button)
        logger.info("Click at (%d, %d) button=%s x%d", req.x, req.y, req.button, req.clicks)
        return {"success": True, "x": req.x, "y": req.y}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/input/move")
async def move_mouse(req: MoveRequest):
    try:
        pyautogui.moveTo(req.x, req.y, duration=req.duration)
        return {"success": True, "x": req.x, "y": req.y}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/input/scroll")
async def scroll(req: ScrollRequest):
    try:
        if req.x is not None and req.y is not None:
            pyautogui.scroll(req.clicks, x=req.x, y=req.y)
        else:
            pyautogui.scroll(req.clicks)
        direction = "up" if req.clicks > 0 else "down"
        logger.info("Scroll %s by %d", direction, abs(req.clicks))
        return {"success": True, "direction": direction, "clicks": abs(req.clicks)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/input/drag")
async def drag(req: DragRequest):
    try:
        pyautogui.moveTo(req.start_x, req.start_y)
        pyautogui.drag(
            req.end_x - req.start_x,
            req.end_y - req.start_y,
            duration=req.duration,
            button=req.button,
        )
        logger.info(
            "Drag (%d,%d)->(%d,%d)",
            req.start_x, req.start_y, req.end_x, req.end_y,
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/input/mouse_position")
async def mouse_position():
    pos = pyautogui.position()
    return {"x": pos.x, "y": pos.y}


@router.get("/input/screen_size")
async def screen_size():
    size = pyautogui.size()
    return {"width": size.width, "height": size.height}
