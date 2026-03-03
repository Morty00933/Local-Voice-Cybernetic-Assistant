"""Application launch/close routes."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import APP_REGISTRY
from ..safety import is_blocked_command

logger = logging.getLogger(__name__)
router = APIRouter(tags=["apps"])


class AppLaunchRequest(BaseModel):
    app: str
    args: Optional[str] = None


class AppCloseRequest(BaseModel):
    name: Optional[str] = None
    pid: Optional[int] = None


def _find_windows_app(name: str) -> str | None:
    """Search common Windows install locations for an app."""
    user_home = Path.home()
    candidates = [
        # AppData\Local (Discord, Telegram, etc.)
        user_home / "AppData" / "Local",
        # Start Menu shortcuts
        user_home / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"),
        # Program Files
        Path(r"C:\Program Files"),
        Path(r"C:\Program Files (x86)"),
    ]

    name_lower = name.lower()

    # Search for .lnk shortcuts in Start Menu
    for base in candidates:
        if not base.exists():
            continue
        for p in base.rglob("*.lnk"):
            if name_lower in p.stem.lower():
                return str(p)
        # Also search for .exe
        for p in base.rglob(f"*{name_lower}*.exe"):
            return str(p)

    return None


@router.post("/app/launch")
async def launch_app(req: AppLaunchRequest):
    app_name = req.app.lower().strip()
    executable = APP_REGISTRY.get(app_name, app_name)

    cmd_str = f"{executable} {req.args}" if req.args else executable
    if is_blocked_command(cmd_str):
        return {"success": False, "error": "Command blocked by safety rules"}

    method = "unknown"
    try:
        if sys.platform == "win32":
            args_list = req.args.split() if req.args else []

            # Strategy 1: executable is in PATH (notepad, calc, explorer, etc.)
            exe_path = shutil.which(executable)
            if exe_path:
                method = "which"
                subprocess.Popen(
                    [exe_path] + args_list,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # Strategy 2: os.startfile — handles .lnk, protocols, registered apps
                try:
                    method = "startfile"
                    if args_list:
                        os.startfile(executable, "open")
                    else:
                        os.startfile(executable)
                except OSError:
                    # Strategy 3: search common install paths
                    found = _find_windows_app(executable)
                    if found:
                        method = f"found:{found}"
                        os.startfile(found)
                    else:
                        # Strategy 4: fallback to shell start
                        method = "shell-start"
                        subprocess.Popen(
                            f'start "" "{executable}"',
                            shell=True,
                        )
        else:
            cmd = [executable]
            if req.args:
                cmd.extend(req.args.split())
            subprocess.Popen(cmd, start_new_session=True)
            method = "popen"

        logger.info("Launched app=%s executable=%s method=%s", app_name, executable, method)
        return {"success": True, "app": app_name, "executable": executable, "method": method}

    except Exception as e:
        logger.error("Failed to launch %s: %s", app_name, e)
        return {"success": False, "error": str(e)}


@router.post("/app/close")
async def close_app(req: AppCloseRequest):
    import psutil

    if not req.name and not req.pid:
        return {"success": False, "error": "Provide 'name' or 'pid'"}

    closed = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = proc.info["name"].lower()
                if req.pid and proc.info["pid"] == req.pid:
                    proc.terminate()
                    closed.append(proc.info["name"])
                elif req.name and req.name.lower() in pname:
                    proc.terminate()
                    closed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed:
            logger.info("Closed: %s", closed)
            return {"success": True, "closed": closed}
        else:
            return {"success": False, "error": f"No matching process found for '{req.name or req.pid}'"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/app/list")
async def list_known_apps():
    return {"apps": list(APP_REGISTRY.keys())}
