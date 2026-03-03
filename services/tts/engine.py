"""TTS engines: XTTS-v2 (GPU) and Piper (CPU fallback)."""
from __future__ import annotations

import io
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np

from shared.config import settings

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Abstract TTS engine."""

    @abstractmethod
    def synthesize(self, text: str, speaker_wav: str | None = None) -> tuple[np.ndarray, int]:
        """Synthesize speech. Returns (audio_array, sample_rate)."""
        ...

    @abstractmethod
    def unload(self) -> None:
        ...


class XTTSEngine(TTSEngine):
    """Coqui XTTS-v2 engine (GPU, supports voice cloning)."""

    def __init__(
        self,
        model_path: str | None = None,
        device: str | None = None,
        language: str = "ru",
    ):
        self.model_path = model_path or os.environ.get("TTS_MODEL_PATH", "tts_models/multilingual/multi-dataset/xtts_v2")
        self.device = device or settings.tts.device
        self.language = language
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        t0 = time.time()
        try:
            from TTS.api import TTS
            self._model = TTS(model_name=self.model_path).to(self.device)
            logger.info("XTTS-v2 loaded in %.2fs on %s", time.time() - t0, self.device)
        except Exception as e:
            logger.error("Failed to load XTTS-v2: %s", e)
            raise

    def synthesize(self, text: str, speaker_wav: str | None = None) -> tuple[np.ndarray, int]:
        self._load()
        t0 = time.time()

        wav = self._model.tts(
            text=text,
            speaker_wav=speaker_wav,
            language=self.language,
        )
        audio = np.array(wav, dtype=np.float32)
        sr = self._model.synthesizer.output_sample_rate

        logger.info("XTTS synthesized %d samples in %.2fs", len(audio), time.time() - t0)
        return audio, sr

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("XTTS-v2 unloaded")


class PiperEngine(TTSEngine):
    """Piper TTS engine (CPU, fast, lightweight)."""

    def __init__(self, model_path: str | None = None, voice: str = "ru_RU-irina-medium"):
        self.model_path = model_path
        self.voice = voice
        self._piper: Any = None

    def _load(self) -> None:
        if self._piper is not None:
            return
        try:
            from piper import PiperVoice
            model = self.model_path or os.environ.get("PIPER_MODEL", f"/models/piper/{self.voice}.onnx")
            self._piper = PiperVoice.load(model)
            logger.info("Piper TTS loaded: %s", self.voice)
        except Exception as e:
            logger.error("Failed to load Piper: %s", e)
            raise

    def synthesize(self, text: str, speaker_wav: str | None = None) -> tuple[np.ndarray, int]:
        self._load()
        t0 = time.time()

        audio_bytes = io.BytesIO()
        import wave
        with wave.open(audio_bytes, "wb") as wf:
            self._piper.synthesize(text, wf)

        audio_bytes.seek(0)
        with wave.open(audio_bytes, "rb") as wf:
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        logger.info("Piper synthesized %d samples in %.2fs", len(audio), time.time() - t0)
        return audio, sr

    def unload(self) -> None:
        self._piper = None
        logger.info("Piper TTS unloaded")


def create_engine() -> TTSEngine:
    """Create TTS engine based on config."""
    engine_type = settings.tts.engine.lower()

    if engine_type == "xtts":
        return XTTSEngine()
    elif engine_type == "piper":
        return PiperEngine()
    else:
        # Auto-detect: try XTTS first, fall back to Piper
        try:
            e = XTTSEngine()
            e._load()
            return e
        except Exception:
            logger.warning("XTTS unavailable, falling back to Piper")
            return PiperEngine()
