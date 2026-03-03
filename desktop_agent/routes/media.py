"""Media control and volume management."""
from __future__ import annotations

import logging
import sys
from typing import Optional

import pyautogui
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["media"])


class VolumeRequest(BaseModel):
    level: Optional[int] = None  # 0-100, None = get current
    mute: Optional[bool] = None


# ── Volume (Windows only via pycaw) ──────────────────────────────

def _get_volume_interface():
    """Get Windows audio endpoint volume interface."""
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


@router.get("/media/volume")
async def get_volume():
    if sys.platform != "win32":
        return {"success": False, "error": "Volume control is Windows-only"}
    try:
        vol = _get_volume_interface()
        level = round(vol.GetMasterVolumeLevelScalar() * 100)
        muted = bool(vol.GetMute())
        return {"success": True, "level": level, "muted": muted}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/media/volume")
async def set_volume(req: VolumeRequest):
    if sys.platform != "win32":
        return {"success": False, "error": "Volume control is Windows-only"}
    try:
        vol = _get_volume_interface()
        if req.level is not None:
            clamped = max(0, min(100, req.level))
            vol.SetMasterVolumeLevelScalar(clamped / 100, None)
            logger.info("Volume set to %d%%", clamped)
        if req.mute is not None:
            vol.SetMute(int(req.mute), None)
            logger.info("Mute: %s", req.mute)

        level = round(vol.GetMasterVolumeLevelScalar() * 100)
        muted = bool(vol.GetMute())
        return {"success": True, "level": level, "muted": muted}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Media keys ───────────────────────────────────────────────────

@router.post("/media/play_pause")
async def media_play_pause():
    try:
        pyautogui.press("playpause")
        return {"success": True, "action": "play_pause"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/media/next")
async def media_next():
    try:
        pyautogui.press("nexttrack")
        return {"success": True, "action": "next_track"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/media/prev")
async def media_prev():
    try:
        pyautogui.press("prevtrack")
        return {"success": True, "action": "prev_track"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/media/stop")
async def media_stop():
    try:
        pyautogui.press("stop")
        return {"success": True, "action": "stop"}
    except Exception as e:
        return {"success": False, "error": str(e)}
