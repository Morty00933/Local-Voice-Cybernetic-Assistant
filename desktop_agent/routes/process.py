"""Process management routes."""
from __future__ import annotations

import logging
from typing import Optional

import psutil
from fastapi import APIRouter
from pydantic import BaseModel

from ..safety import is_protected_process

logger = logging.getLogger(__name__)
router = APIRouter(tags=["process"])


class ProcessKillRequest(BaseModel):
    pid: Optional[int] = None
    name: Optional[str] = None


@router.get("/process/list")
async def list_processes(top: int = 30, sort_by: str = "memory"):
    """List running processes, sorted by CPU or memory usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            info = p.info
            mem_mb = round(info["memory_info"].rss / (1024 * 1024), 1) if info["memory_info"] else 0
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu_percent": info["cpu_percent"] or 0,
                "memory_mb": mem_mb,
                "status": info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key = "memory_mb" if sort_by == "memory" else "cpu_percent"
    procs.sort(key=lambda x: x[key], reverse=True)
    return {"success": True, "processes": procs[:top], "total": len(procs)}


@router.post("/process/kill")
async def kill_process(req: ProcessKillRequest):
    if not req.pid and not req.name:
        return {"success": False, "error": "Provide 'pid' or 'name'"}

    killed = []
    errors = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            pname = p.info["name"]
            match = False
            if req.pid and p.info["pid"] == req.pid:
                match = True
            elif req.name and req.name.lower() in pname.lower():
                match = True

            if match:
                if is_protected_process(pname):
                    errors.append(f"{pname} (PID {p.info['pid']}) is a protected system process")
                    continue
                p.terminate()
                killed.append({"pid": p.info["pid"], "name": pname})
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            errors.append(str(e))
            continue

    if killed:
        logger.info("Killed processes: %s", killed)
        return {"success": True, "killed": killed, "errors": errors or None}
    return {"success": False, "error": "No matching process found", "details": errors or None}


@router.get("/process/{pid}")
async def process_info(pid: int):
    """Get detailed info about a specific process."""
    try:
        p = psutil.Process(pid)
        info = p.as_dict(attrs=[
            "pid", "name", "exe", "cmdline", "status",
            "cpu_percent", "memory_info", "create_time",
            "num_threads", "username",
        ])
        if info.get("memory_info"):
            info["memory_mb"] = round(info["memory_info"].rss / (1024 * 1024), 1)
            del info["memory_info"]
        return {"success": True, "process": info}
    except psutil.NoSuchProcess:
        return {"success": False, "error": f"Process {pid} not found"}
    except psutil.AccessDenied:
        return {"success": False, "error": f"Access denied for PID {pid}"}
