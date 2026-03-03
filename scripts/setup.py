#!/usr/bin/env python3
"""LVCA Setup — download all required models on first run."""
from __future__ import annotations

import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODELS = [
    os.environ.get("OLLAMA_MODEL_CHAT", "qwen2.5:7b-instruct-q4_K_M"),
    os.environ.get("OLLAMA_MODEL_EMBED", "nomic-embed-text"),
]

PIPER_VOICE = os.environ.get("PIPER_VOICE", "ru_RU-irina-medium")
PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
PIPER_DIR = Path("models/piper")

REQUIRED_INFRA = ["ollama", "qdrant", "redis"]


def _print(icon: str, msg: str) -> None:
    print(f"  {icon} {msg}")


def _ok(msg: str) -> None:
    _print("[OK]", msg)


def _fail(msg: str) -> None:
    _print("[!!]", msg)


def _info(msg: str) -> None:
    _print("[..]", msg)


# ── Step 1: Start infrastructure ─────────────────────────────────
def start_infra() -> bool:
    print("\n=== Step 1: Starting infrastructure ===")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"] + REQUIRED_INFRA,
            check=True,
            capture_output=True,
            text=True,
        )
        _ok("Infrastructure started (ollama, qdrant, redis)")
        return True
    except subprocess.CalledProcessError as e:
        _fail(f"Failed to start infrastructure: {e.stderr}")
        return False
    except FileNotFoundError:
        _fail("Docker not found. Install Docker Desktop first.")
        return False


# ── Step 2: Wait for Ollama ──────────────────────────────────────
def wait_for_ollama(timeout: int = 60) -> bool:
    print("\n=== Step 2: Waiting for Ollama ===")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    _ok("Ollama is ready")
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    _fail(f"Ollama not ready after {timeout}s")
    return False


# ── Step 3: Pull Ollama models ───────────────────────────────────
def pull_ollama_models() -> list[tuple[str, bool]]:
    print("\n=== Step 3: Pulling Ollama models ===")
    results = []

    # Check which models already exist
    existing = set()
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for m in data.get("models", []):
                existing.add(m.get("name", ""))
    except Exception:
        pass

    for model in OLLAMA_MODELS:
        if model in existing:
            _ok(f"{model} (already downloaded)")
            results.append((model, True))
            continue

        _info(f"Pulling {model} (this may take a while)...")
        try:
            payload = json.dumps({"name": model, "stream": False}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                if resp.status == 200:
                    _ok(f"{model} downloaded")
                    results.append((model, True))
                else:
                    _fail(f"{model} pull returned status {resp.status}")
                    results.append((model, False))
        except Exception as e:
            _fail(f"{model} pull failed: {e}")
            results.append((model, False))

    return results


# ── Step 4: Download Piper TTS model ────────────────────────────
def download_piper_model() -> bool:
    print("\n=== Step 4: Downloading Piper TTS model ===")

    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = PIPER_DIR / f"{PIPER_VOICE}.onnx"
    json_path = PIPER_DIR / f"{PIPER_VOICE}.onnx.json"

    # Language code extraction: ru_RU-irina-medium → ru/ru_RU/irina/medium
    parts = PIPER_VOICE.split("-")
    lang_code = parts[0][:2]  # "ru"
    lang_full = parts[0]      # "ru_RU"
    speaker = parts[1]        # "irina"
    quality = parts[2]        # "medium"

    base = f"{PIPER_BASE_URL}/{lang_code}/{lang_full}/{speaker}/{quality}"

    for fname, fpath in [(f"{PIPER_VOICE}.onnx", onnx_path), (f"{PIPER_VOICE}.onnx.json", json_path)]:
        if fpath.exists() and fpath.stat().st_size > 1000:
            _ok(f"{fname} (already exists)")
            continue

        url = f"{base}/{fname}"
        _info(f"Downloading {fname}...")
        try:
            urllib.request.urlretrieve(url, str(fpath))
            _ok(f"{fname} ({fpath.stat().st_size // 1024 // 1024}MB)")
        except Exception as e:
            _fail(f"Failed to download {fname}: {e}")
            return False

    return True


# ── Step 5: Verify STT note ─────────────────────────────────────
def stt_note() -> None:
    print("\n=== Step 5: STT (Faster Whisper) ===")
    _ok("STT model will auto-download on first container start")
    _info("Model: large-v3-turbo (~1.5GB), cached in Docker volume")


# ── Summary ──────────────────────────────────────────────────────
def main() -> int:
    print("=" * 50)
    print("  LVCA Setup — Model Downloader")
    print("=" * 50)

    checks: list[tuple[str, bool]] = []

    # 1. Infra
    ok = start_infra()
    checks.append(("Infrastructure", ok))
    if not ok:
        print("\nCannot continue without Docker infrastructure.")
        return 1

    # 2. Wait for Ollama
    ok = wait_for_ollama()
    checks.append(("Ollama ready", ok))
    if not ok:
        print("\nCannot continue without Ollama.")
        return 1

    # 3. Ollama models
    model_results = pull_ollama_models()
    for model, ok in model_results:
        checks.append((f"Model: {model}", ok))

    # 4. Piper
    ok = download_piper_model()
    checks.append(("Piper TTS model", ok))

    # 5. STT note
    stt_note()
    checks.append(("STT (auto-download)", True))

    # Summary
    print("\n" + "=" * 50)
    print("  Setup Summary")
    print("=" * 50)
    all_ok = True
    for name, ok in checks:
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nAll models ready! Start LVCA:")
        print("  make up        # start all services")
        print("  make chat      # test text chat")
    else:
        print("\nSome steps failed. Fix the issues and re-run: make setup")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
