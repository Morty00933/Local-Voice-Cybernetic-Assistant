"""Desktop notifications."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notify"])


class NotifyRequest(BaseModel):
    title: str = "LVCA"
    message: str
    timeout: int = 10  # seconds


@router.post("/notify")
async def send_notification(req: NotifyRequest):
    try:
        from plyer import notification

        notification.notify(
            title=req.title,
            message=req.message,
            timeout=req.timeout,
            app_name="LVCA",
        )
        logger.info("Notification sent: %s", req.title)
        return {"success": True, "title": req.title}
    except Exception as e:
        logger.error("Notification failed: %s", e)
        return {"success": False, "error": str(e)}
