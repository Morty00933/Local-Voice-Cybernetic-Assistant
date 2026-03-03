#!/usr/bin/env python3
"""LVCA Native Launcher — start all services without Docker.

Usage:
    python scripts/native_up.py          # start all
    python scripts/native_up.py --stop   # stop all
    python scripts/native_up.py --infra  # start only infra (ollama, qdrant, redis)

Ports (native):
    STT          → :8001
    Brain        → :8002
    TTS          → :8003
    Orchestrator → :8000
    Desktop Agent→ :9100
    Ollama       → :11434
    Qdrant       → :6333
    Redis        → :6379
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
PID_DIR = ROOT / ".pids"

# ── Environment for native mode ─────────────────────────────────

NATIVE_ENV: Dict[str, str] = {
    **os.environ,
    # Ollama
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL_CHAT": os.environ.get("OLLAMA_MODEL_CHAT", "qwen2.5:7b-instruct-q4_K_M"),
    "OLLAMA_MODEL_EMBED": os.environ.get("OLLAMA_MODEL_EMBED", "nomic-embed-text"),
    # Qdrant
    "QDRANT_URL": "http://localhost:6333",
    "QDRANT_COLLECTION": os.environ.get("QDRANT_COLLECTION", "lvca_knowledge"),
    # Redis
    "REDIS_URL": "redis://localhost:6379/0",
    "REDIS_HOST": "localhost",
    # Orchestrator → services
    "STT_SERVICE_URL": "http://localhost:8001",
    "BRAIN_SERVICE_URL": "http://localhost:8002",
    "TTS_SERVICE_URL": "http://localhost:8003",
    # Desktop agent
    "DESKTOP_AGENT_URL": "http://localhost:9100",
    # STT
    "STT_DEVICE": os.environ.get("STT_DEVICE", "auto"),
    "STT_COMPUTE_TYPE": os.environ.get("STT_COMPUTE_TYPE", "float16"),
    "STT_MODEL_SIZE": os.environ.get("STT_MODEL_SIZE", "large-v3-turbo"),
    "STT_MODEL_CACHE": str(ROOT / "models"),
    # TTS
    "TTS_ENGINE": os.environ.get("TTS_ENGINE", "piper"),
    "TTS_DEVICE": os.environ.get("TTS_DEVICE", "cpu"),
    "VOICES_DIR": str(ROOT / "voices"),
    # Brain
    "EMBED_PROVIDER": "ollama",
    # Logging
    "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
    "PYTHONPATH": str(ROOT),
}

# ── Service definitions ──────────────────────────────────────────

SERVICES = {
    "stt": {
        "cmd": [sys.executable, "-m", "uvicorn",
                "services.stt.streaming:app",
                "--host", "0.0.0.0", "--port", "8001"],
        "port": 8001,
        "health": "http://localhost:8001/health",
    },
    "brain": {
        "cmd": [sys.executable, "-m", "uvicorn",
                "services.brain.streaming:app",
                "--host", "0.0.0.0", "--port", "8002"],
        "port": 8002,
        "health": "http://localhost:8002/health",
    },
    "tts": {
        "cmd": [sys.executable, "-m", "uvicorn",
                "services.tts.streaming:app",
                "--host", "0.0.0.0", "--port", "8003"],
        "port": 8003,
        "health": "http://localhost:8003/health",
    },
    "orchestrator": {
        "cmd": [sys.executable, "-m", "uvicorn",
                "orchestrator.main:app",
                "--host", "0.0.0.0", "--port", "8000"],
        "port": 8000,
        "health": "http://localhost:8000/api/health",
    },
    "desktop-agent": {
        "cmd": [sys.executable, "-m", "desktop_agent.main"],
        "port": 9100,
        "health": "http://localhost:9100/health",
    },
}


def _pid_file(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def _save_pid(name: str, pid: int) -> None:
    PID_DIR.mkdir(exist_ok=True)
    _pid_file(name).write_text(str(pid))


def _read_pid(name: str) -> Optional[int]:
    f = _pid_file(name)
    if f.exists():
        try:
            return int(f.read_text().strip())
        except ValueError:
            pass
    return None


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_service(name: str, info: dict) -> Optional[subprocess.Popen]:
    """Start a service, skip if already running."""
    existing = _read_pid(name)
    if existing and _is_alive(existing):
        print(f"  [{name}] already running (PID {existing})")
        return None

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{name}.log"

    print(f"  [{name}] starting on :{info['port']}...")
    proc = subprocess.Popen(
        info["cmd"],
        cwd=str(ROOT),
        env=NATIVE_ENV,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    _save_pid(name, proc.pid)
    return proc


def stop_service(name: str) -> None:
    """Stop a service by PID file."""
    pid = _read_pid(name)
    if pid and _is_alive(pid):
        print(f"  [{name}] stopping (PID {pid})...")
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"  [{name}] error stopping: {e}")
    else:
        print(f"  [{name}] not running")
    _pid_file(name).unlink(missing_ok=True)


def check_health(name: str, url: str, timeout: float = 2.0) -> bool:
    """Quick health check."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_healthy(services: Dict[str, dict], max_wait: int = 60) -> None:
    """Wait for services to become healthy."""
    start = time.time()
    pending = set(services.keys())
    while pending and (time.time() - start) < max_wait:
        for name in list(pending):
            if check_health(name, services[name]["health"]):
                print(f"  [{name}] healthy!")
                pending.discard(name)
        if pending:
            time.sleep(2)
    if pending:
        print(f"  WARNING: still not healthy: {', '.join(pending)}")
        print(f"  Check logs in {ROOT / 'logs'}")


def check_infra() -> Dict[str, bool]:
    """Check if infrastructure services are reachable."""
    results = {}
    for name, url in [("ollama", "http://localhost:11434/api/tags"),
                       ("qdrant", "http://localhost:6333/healthz"),
                       ("redis", None)]:
        if url:
            results[name] = check_health(name, url)
        else:
            try:
                import socket
                s = socket.socket()
                s.settimeout(2)
                s.connect(("localhost", 6379))
                s.close()
                results[name] = True
            except Exception:
                results[name] = False
    return results


def start_infra_docker() -> None:
    """Start only infra containers (ollama, qdrant, redis) via Docker."""
    print("\n  Starting infra (Docker)...")
    subprocess.run(
        ["docker", "compose", "up", "-d", "ollama", "qdrant", "redis"],
        cwd=str(ROOT),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LVCA Native Launcher")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--infra", action="store_true", help="Start only infra")
    parser.add_argument("--no-infra", action="store_true",
                        help="Skip infra check (assume already running)")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()

    if args.stop:
        print("Stopping LVCA services...")
        for name in SERVICES:
            stop_service(name)
        print("Done.")
        return

    if args.status:
        print("LVCA Service Status:")
        infra = check_infra()
        for name, ok in infra.items():
            status = "UP" if ok else "DOWN"
            print(f"  [{name}] {status}")
        for name, info in SERVICES.items():
            pid = _read_pid(name)
            alive = pid and _is_alive(pid)
            healthy = check_health(name, info["health"]) if alive else False
            status = "HEALTHY" if healthy else ("RUNNING" if alive else "DOWN")
            pid_str = f" (PID {pid})" if pid else ""
            print(f"  [{name}] {status}{pid_str} → :{info['port']}")
        return

    print("=" * 50)
    print("  LVCA Native Mode")
    print("=" * 50)

    # 1. Check infra
    if not args.no_infra:
        print("\nChecking infrastructure...")
        infra = check_infra()
        missing = [k for k, v in infra.items() if not v]
        if missing:
            print(f"  Missing: {', '.join(missing)}")
            if args.infra:
                start_infra_docker()
                print("  Waiting for infra...")
                time.sleep(5)
            else:
                start_infra_docker()
                time.sleep(5)
        else:
            print("  All infrastructure OK")

        if args.infra:
            return

    # 2. Start application services
    print("\nStarting services...")
    order = ["stt", "brain", "tts", "orchestrator", "desktop-agent"]
    for name in order:
        start_service(name, SERVICES[name])
        time.sleep(1)  # stagger starts

    # 3. Wait for health
    print("\nWaiting for services to start...")
    wait_healthy(SERVICES, max_wait=90)

    print("\n" + "=" * 50)
    print("  LVCA is ready!")
    print(f"  App:    make app")
    print(f"  Health: http://localhost:8000/api/health")
    print(f"  Logs:   {ROOT / 'logs'}")
    print(f"  Stop:   make native-down")
    print("=" * 50)


if __name__ == "__main__":
    main()
