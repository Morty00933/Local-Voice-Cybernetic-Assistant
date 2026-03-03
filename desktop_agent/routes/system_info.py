"""System information routes."""
from __future__ import annotations

import logging
import platform

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/system/info")
async def system_info():
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "hostname": platform.node(),
        "cpu": {
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "percent": cpu_percent,
            "freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk.percent,
        },
    }

    # GPU info
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        info["gpu"] = [
            {
                "name": g.name,
                "memory_total_mb": g.memoryTotal,
                "memory_used_mb": g.memoryUsed,
                "memory_free_mb": g.memoryFree,
                "load_percent": round(g.load * 100, 1),
                "temperature": g.temperature,
            }
            for g in gpus
        ]
    except Exception:
        info["gpu"] = []

    return info
