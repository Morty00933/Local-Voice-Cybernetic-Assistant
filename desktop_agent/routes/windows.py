"""Window management routes."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["windows"])


class WindowAction(BaseModel):
    action: str  # list, focus, minimize, maximize, restore, resize, move, close
    title: Optional[str] = None
    hwnd: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None


def _find_windows(title: str | None = None) -> list[dict]:
    """Find windows, optionally filtering by title substring."""
    import pygetwindow as gw

    all_wins = gw.getAllWindows()
    results = []
    for w in all_wins:
        if not w.title.strip():
            continue
        if title and title.lower() not in w.title.lower():
            continue
        results.append({
            "title": w.title,
            "hwnd": w._hWnd,
            "left": w.left,
            "top": w.top,
            "width": w.width,
            "height": w.height,
            "visible": w.visible,
            "minimized": w.isMinimized,
            "maximized": w.isMaximized,
            "active": w.isActive,
        })
    return results


def _get_window(title: str | None = None, hwnd: int | None = None):
    """Get a single window by title or hwnd."""
    import pygetwindow as gw

    if hwnd:
        try:
            return gw.Win32Window(hwnd)
        except Exception:
            pass

    if title:
        wins = _find_windows(title)
        if wins:
            return gw.Win32Window(wins[0]["hwnd"])

    return None


@router.post("/window")
async def window_action(req: WindowAction):
    action = req.action.lower()

    try:
        if action == "list":
            windows = _find_windows(req.title)
            return {"success": True, "windows": windows}

        win = _get_window(req.title, req.hwnd)
        if not win:
            return {"success": False, "error": f"Window not found: {req.title or req.hwnd}"}

        if action == "focus":
            if win.isMinimized:
                win.restore()
            win.activate()
            return {"success": True, "action": "focus", "title": win.title}

        elif action == "minimize":
            win.minimize()
            return {"success": True, "action": "minimize", "title": win.title}

        elif action == "maximize":
            win.maximize()
            return {"success": True, "action": "maximize", "title": win.title}

        elif action == "restore":
            win.restore()
            return {"success": True, "action": "restore", "title": win.title}

        elif action == "resize":
            if req.width and req.height:
                win.resizeTo(req.width, req.height)
                return {"success": True, "action": "resize", "title": win.title}
            return {"success": False, "error": "width and height required"}

        elif action == "move":
            if req.x is not None and req.y is not None:
                win.moveTo(req.x, req.y)
                return {"success": True, "action": "move", "title": win.title}
            return {"success": False, "error": "x and y required"}

        elif action == "close":
            win.close()
            return {"success": True, "action": "close", "title": win.title}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error("Window action '%s' failed: %s", action, e, exc_info=True)
        return {"success": False, "error": str(e)}
