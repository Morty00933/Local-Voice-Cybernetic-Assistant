"""Microphone capture using PyAudio — PCM int16, 16kHz, mono."""
from __future__ import annotations

import io
import logging
import struct
import wave
import threading
from typing import Callable

logger = logging.getLogger(__name__)

RATE = 16000
CHANNELS = 1
FORMAT_WIDTH = 2  # int16
CHUNK = 1024


class MicCapture:
    """Push-to-talk microphone capture."""

    def __init__(self):
        self._pa = None
        self._stream = None
        self._frames: list[bytes] = []
        self._recording = False
        self._lock = threading.Lock()

    def _ensure_pa(self):
        if self._pa is None:
            import pyaudio
            self._pa = pyaudio.PyAudio()

    def start(self) -> None:
        """Start recording."""
        import pyaudio
        self._ensure_pa()
        with self._lock:
            self._frames = []
            self._recording = True
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                stream_callback=self._callback,
            )
            self._stream.start_stream()
            logger.info("Mic recording started")

    def _callback(self, in_data, frame_count, time_info, status):
        import pyaudio
        if self._recording:
            self._frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        with self._lock:
            self._recording = False
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            logger.info("Mic recording stopped, %d frames", len(self._frames))
            return self._to_wav(self._frames)

    def _to_wav(self, frames: list[bytes]) -> bytes:
        """Convert raw PCM frames to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(FORMAT_WIDTH)
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def close(self) -> None:
        if self._stream:
            self._stream.close()
        if self._pa:
            self._pa.terminate()
            self._pa = None
