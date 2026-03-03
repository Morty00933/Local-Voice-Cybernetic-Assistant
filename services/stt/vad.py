"""Voice Activity Detection wrapper for streaming STT."""
from __future__ import annotations

import logging
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

TARGET_SR = 16000


class VoiceActivityDetector:
    """Streaming VAD: accumulates audio chunks, emits speech segments."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_ms: int = 300,
        min_silence_ms: int = 500,
        speech_pad_ms: int = 200,
        max_speech_s: float = 30.0,
        on_speech: Optional[Callable[[np.ndarray], None]] = None,
    ):
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.speech_pad_ms = speech_pad_ms
        self.max_speech_s = max_speech_s
        self.on_speech = on_speech

        self._buffer: list[np.ndarray] = []
        self._is_speaking = False
        self._silence_frames = 0
        self._vad_model = None
        self._loaded = False

    def _load_model(self) -> None:
        if self._loaded:
            return
        import torch
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        self._vad_model = model
        self._loaded = True
        logger.info("Streaming VAD model loaded")

    def _get_confidence(self, chunk: np.ndarray) -> float:
        import torch
        self._load_model()
        tensor = torch.tensor(chunk, dtype=torch.float32)
        return float(self._vad_model(tensor, TARGET_SR))

    def process_chunk(self, chunk: np.ndarray) -> Optional[np.ndarray]:
        """Process an audio chunk. Returns speech segment if a phrase boundary is detected."""
        if chunk.dtype != np.float32:
            chunk = chunk.astype(np.float32)

        confidence = self._get_confidence(chunk)

        if confidence >= self.threshold:
            self._buffer.append(chunk)
            self._is_speaking = True
            self._silence_frames = 0
        elif self._is_speaking:
            self._buffer.append(chunk)
            self._silence_frames += 1
            silence_duration_ms = self._silence_frames * len(chunk) / TARGET_SR * 1000

            if silence_duration_ms >= self.min_silence_ms:
                return self._flush()
        else:
            # Not speaking, no buffer
            self._silence_frames = 0

        # Check max speech duration
        if self._buffer:
            total_samples = sum(len(c) for c in self._buffer)
            if total_samples / TARGET_SR >= self.max_speech_s:
                return self._flush()

        return None

    def _flush(self) -> Optional[np.ndarray]:
        if not self._buffer:
            return None
        speech = np.concatenate(self._buffer)
        self._buffer.clear()
        self._is_speaking = False
        self._silence_frames = 0

        duration_ms = len(speech) / TARGET_SR * 1000
        if duration_ms < self.min_speech_ms:
            return None

        if self.on_speech:
            self.on_speech(speech)
        return speech

    def finalize(self) -> Optional[np.ndarray]:
        """Flush any remaining buffered audio."""
        return self._flush()

    def reset(self) -> None:
        self._buffer.clear()
        self._is_speaking = False
        self._silence_frames = 0
