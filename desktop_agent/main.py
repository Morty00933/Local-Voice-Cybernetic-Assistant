"""LVCA Desktop Agent — native Windows process for desktop automation."""
from __future__ import annotations

import logging
import platform

import pyautogui
from fastapi import FastAPI

from . import config

# Configure pyautogui
pyautogui.PAUSE = config.PYAUTOGUI_PAUSE
pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("desktop_agent")

app = FastAPI(title="LVCA Desktop Agent", version="0.1.0")

# ── Import and register routes ────────────────────────────────────
from .routes import apps, windows, input as input_routes  # noqa: E402
from .routes import screenshot, clipboard, media  # noqa: E402
from .routes import process, system_info, notify  # noqa: E402

app.include_router(apps.router, prefix="/api")
app.include_router(windows.router, prefix="/api")
app.include_router(input_routes.router, prefix="/api")
app.include_router(screenshot.router, prefix="/api")
app.include_router(clipboard.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(process.router, prefix="/api")
app.include_router(system_info.router, prefix="/api")
app.include_router(notify.router, prefix="/api")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "platform": platform.system(),
        "hostname": platform.node(),
    }


def run():
    """Entry point for running the Desktop Agent."""
    import uvicorn
    logger.info("Starting Desktop Agent on %s:%s", config.HOST, config.PORT)
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    run()
