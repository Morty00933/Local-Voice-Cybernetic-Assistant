"""Audio playback using sounddevice."""
from __future__ import annotations

import io
import logging
import threading
import wave

import numpy as np

logger = logging.getLogger(__name__)


def play_wav_bytes(wav_bytes: bytes) -> None:
    """Play WAV audio bytes in a background thread (non-blocking)."""
    def _play():
        try:
            import sounddevice as sd
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                sr = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                if channels > 1:
                    audio = audio.reshape(-1, channels)
                sd.play(audio, samplerate=sr)
                sd.wait()
        except Exception as e:
            logger.error("Playback error: %s", e)

    t = threading.Thread(target=_play, daemon=True)
    t.start()
