"""Clipboard operations."""
from __future__ import annotations

import logging

import pyperclip
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["clipboard"])


class ClipboardSetRequest(BaseModel):
    text: str


@router.get("/clipboard")
async def get_clipboard():
    try:
        text = pyperclip.paste()
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/clipboard")
async def set_clipboard(req: ClipboardSetRequest):
    try:
        pyperclip.copy(req.text)
        logger.info("Clipboard set (%d chars)", len(req.text))
        return {"success": True, "chars": len(req.text)}
    except Exception as e:
        return {"success": False, "error": str(e)}
