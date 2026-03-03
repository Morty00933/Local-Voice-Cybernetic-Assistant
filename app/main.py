"""LVCA Desktop Application — CustomTkinter UI with voice + streaming."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from typing import Any

import customtkinter as ctk

from .ui.chat_frame import ChatFrame
from .ui.voice_frame import VoiceFrame
from .ui.status_bar import StatusBar
from .client.stream import stream_chat
from .audio.capture import MicCapture
from .audio.playback import play_wav_bytes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("lvca-app")

BASE_URL = os.environ.get("LVCA_URL", "http://localhost:8000")
STT_URL = os.environ.get("LVCA_STT_URL", "http://localhost:8001")  # used in voice fallback
SESSION_ID = "desktop-app"


class LVCAApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LVCA")
        self.geometry("700x550")
        self.minsize(500, 400)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Audio
        self._mic = MicCapture()
        self._busy = False

        # Layout
        self._build_ui()

        # Health check loop
        self.after(2000, self._check_health)

    def _build_ui(self) -> None:
        # Chat area (expandable)
        self.chat = ChatFrame(self, on_send=self._on_send)
        self.chat.pack(fill="both", expand=True)

        # Bottom: voice + status
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(0, 4))

        self.voice = VoiceFrame(
            bottom,
            on_start=self._on_mic_start,
            on_stop=self._on_mic_stop,
        )
        self.voice.pack(side="left")

        self.status = StatusBar(bottom)
        self.status.pack(side="right", fill="x", expand=True)

    # ── Text chat ────────────────────────────────────────────────
    def _on_send(self, text: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.chat.set_input_enabled(False)
        self.chat.append_message("user", text)

        # Run streaming in background thread
        t = threading.Thread(target=self._stream_response, args=(text,), daemon=True)
        t.start()

    def _stream_response(self, text: str) -> None:
        """Run in background thread — try SSE streaming, fallback to REST."""
        # Try streaming first, fallback to regular REST if not available
        try:
            self._try_stream(text)
        except Exception:
            self._try_rest_fallback(text)

    def _try_stream(self, text: str) -> None:
        """SSE streaming path."""
        self.after(0, self.chat.start_assistant_message)

        got_response = False

        def on_token(token: str):
            nonlocal got_response
            got_response = True
            self.after(0, self.chat.append_token, token)

        def on_tool(chunk: dict):
            nonlocal got_response
            got_response = True
            name = chunk.get("name", "?")
            status = chunk.get("status", "")
            if status == "running":
                self.after(0, self.chat.append_message, "tool", f"{name} running...")
                self.after(0, self.chat.start_assistant_message)
            elif status == "done":
                output = chunk.get("output", "")[:200]
                self.after(0, self.chat.append_message, "tool", f"{name}: {output}")
                self.after(0, self.chat.start_assistant_message)

        def on_done(full_text: str):
            self.after(0, self.chat.end_assistant_message)
            self.after(0, self._finish_response)

        def on_error(msg: str):
            if not got_response:
                # Streaming failed before any output — raise to trigger fallback
                raise ConnectionError(msg)
            self.after(0, self.chat.append_message, "assistant", f"Error: {msg}")
            self.after(0, self._finish_response)

        stream_chat(
            text=text,
            base_url=BASE_URL,
            session_id=SESSION_ID,
            on_token=on_token,
            on_tool=on_tool,
            on_done=on_done,
            on_error=on_error,
        )

    def _try_rest_fallback(self, text: str) -> None:
        """Fallback: regular REST /api/chat (no streaming)."""
        import httpx
        try:
            with httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0), trust_env=False) as client:
                resp = client.post(
                    f"{BASE_URL}/api/chat",
                    json={"text": text, "session_id": SESSION_ID},
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data.get("text", data.get("response", ""))
                self.after(0, self.chat.append_message, "assistant", reply)
        except Exception as e:
            self.after(0, self.chat.append_message, "assistant", f"Error: {e}")
        finally:
            self.after(0, self._finish_response)

    def _finish_response(self) -> None:
        self._busy = False
        self.chat.set_input_enabled(True)
        self.chat.input_field.focus()

    # ── Voice ────────────────────────────────────────────────────
    def _on_mic_start(self) -> None:
        if self._busy:
            return
        try:
            self._mic.start()
        except Exception as e:
            logger.error("Mic start failed: %s", e)
            self.chat.append_message("assistant", f"Mic error: {e}")

    def _on_mic_stop(self) -> None:
        try:
            wav_bytes = self._mic.stop()
        except Exception as e:
            logger.error("Mic stop failed: %s", e)
            return

        if not wav_bytes or len(wav_bytes) < 1000:
            return

        self._busy = True
        self.chat.set_input_enabled(False)
        self.chat.append_message("user", "(voice input)")

        # Send to voice pipeline in background
        t = threading.Thread(target=self._voice_pipeline, args=(wav_bytes,), daemon=True)
        t.start()

    def _voice_pipeline(self, wav_bytes: bytes) -> None:
        """Send audio to orchestrator /api/chat with audio, get text + optional audio back."""
        import httpx

        try:
            with httpx.Client(timeout=httpx.Timeout(180.0, connect=10.0), trust_env=False) as client:
                resp = client.post(
                    f"{BASE_URL}/api/voice",
                    content=wav_bytes,
                    headers={"Content-Type": "audio/wav"},
                )
                if resp.status_code == 404:
                    # /api/voice not available — fallback: use STT + text chat
                    self._voice_fallback(wav_bytes)
                    return
                resp.raise_for_status()
                data = resp.json()
                text_out = data.get("text_out", data.get("text", ""))
                self.after(0, self.chat.append_message, "assistant", text_out)

                # Play audio if available
                audio = data.get("audio_out")
                if audio:
                    play_wav_bytes(bytes.fromhex(audio) if isinstance(audio, str) else audio)

        except Exception as e:
            logger.error("Voice pipeline failed: %s", e)
            self._voice_fallback(wav_bytes)
        finally:
            self.after(0, self._finish_response)

    def _voice_fallback(self, wav_bytes: bytes) -> None:
        """Fallback: STT transcribe, then text chat."""
        import httpx
        try:
            with httpx.Client(timeout=httpx.Timeout(60.0), trust_env=False) as client:
                # STT
                stt_resp = client.post(
                    f"{STT_URL}/api/transcribe",
                    content=wav_bytes,
                    headers={"Content-Type": "audio/wav"},
                )
                stt_resp.raise_for_status()
                user_text = stt_resp.json().get("text", "")

            if not user_text.strip():
                self.after(0, self.chat.append_message, "assistant", "(empty transcription)")
                return

            self.after(0, self.chat.append_message, "user", f"(voice) {user_text}")
            # Now stream text response
            self.after(0, self.chat.start_assistant_message)

            def on_token(token):
                self.after(0, self.chat.append_token, token)

            def on_done(full_text):
                self.after(0, self.chat.end_assistant_message)

            def on_error(msg):
                self.after(0, self.chat.append_message, "assistant", f"Error: {msg}")

            stream_chat(
                text=user_text,
                base_url=BASE_URL,
                session_id=SESSION_ID,
                on_token=on_token,
                on_done=on_done,
                on_error=on_error,
            )

        except Exception as e:
            self.after(0, self.chat.append_message, "assistant", f"Voice error: {e}")

    # ── Health check ─────────────────────────────────────────────
    def _check_health(self) -> None:
        """Periodic health check of backend services."""
        def _do():
            import httpx
            try:
                with httpx.Client(timeout=httpx.Timeout(3.0), trust_env=False) as client:
                    resp = client.get(f"{BASE_URL}/api/health")
                    if resp.status_code == 200:
                        data = resp.json()
                        services = data.get("services", {})
                        self.after(0, self.status.update_status, services)
            except Exception:
                self.after(0, self.status.update_status, {"brain": False, "tts": False, "stt": False})

        threading.Thread(target=_do, daemon=True).start()
        self.after(15000, self._check_health)  # every 15s

    def on_closing(self) -> None:
        self._mic.close()
        self.destroy()


def main():
    app = LVCAApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
