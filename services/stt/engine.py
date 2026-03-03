"""
Transcription engine using Faster-Whisper (CTranslate2).
Optimized for RTX 3060 12GB VRAM.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import torch
from faster_whisper import WhisperModel

from shared.config import settings

logger = logging.getLogger(__name__)

# Approximate VRAM usage per model size (GB)
_MODEL_VRAM: Dict[str, float] = {
    "tiny": 0.5, "base": 0.5, "small": 1.0,
    "medium": 2.5, "large-v2": 3.5, "large-v3": 3.5,
    "large-v3-turbo": 1.5,
}


@dataclass
class TranscriptionSegment:
    start: float
    end: float
    text: str
    words: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Optional[float] = None


@dataclass
class TranscriptionResult:
    text: str
    segments: List[TranscriptionSegment]
    language: str
    language_probability: float
    duration: float
    processing_time: float


class TranscriptionEngine:
    """Whisper-based transcription engine using Faster-Whisper."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ):
        stt_cfg = settings.stt
        self.model_size = model_size or stt_cfg.model_size
        self.device = self._determine_device(device or stt_cfg.device)
        self.compute_type = compute_type or stt_cfg.compute_type
        if self.device == "cpu":
            self.compute_type = "float32"
        self.model: Optional[WhisperModel] = None

        logger.info(
            "STT engine init: model=%s device=%s compute=%s",
            self.model_size, self.device, self.compute_type,
        )

    def _determine_device(self, device: str) -> str:
        if device != "auto":
            return device
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            required = _MODEL_VRAM.get(self.model_size, 3.0)
            if vram_gb >= required:
                logger.info("Using CUDA (VRAM: %.1fGB, required: %.1fGB)", vram_gb, required)
                return "cuda"
            logger.warning("Insufficient VRAM (%.1fGB < %.1fGB), using CPU", vram_gb, required)
        return "cpu"

    def load_model(self) -> None:
        if self.model is not None:
            return

        t0 = time.time()
        cache_dir = os.environ.get("STT_MODEL_CACHE", "/models")
        local_path = f"{cache_dir}/faster-whisper-{self.model_size}"
        model_path = local_path if os.path.isdir(local_path) else self.model_size

        self.model = WhisperModel(
            model_path,
            device=self.device,
            compute_type=self.compute_type,
            download_root=cache_dir,
            cpu_threads=4,
            num_workers=2,
        )
        logger.info("Whisper model loaded in %.2fs", time.time() - t0)

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        initial_prompt: str | None = None,
        word_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe an audio file."""
        self.load_model()
        t0 = time.time()

        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
            beam_size=5,
            best_of=5,
            patience=1.0,
            temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.9,
            condition_on_previous_text=True,
            initial_prompt=initial_prompt,
            word_timestamps=word_timestamps,
            vad_filter=False,
        )

        segments: List[TranscriptionSegment] = []
        text_parts: List[str] = []

        for seg in segments_gen:
            words = []
            if seg.words:
                words = [
                    {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                    for w in seg.words
                ]
            segments.append(TranscriptionSegment(
                start=seg.start, end=seg.end, text=seg.text.strip(),
                words=words,
                confidence=getattr(seg, "avg_logprob", None),
            ))
            text_parts.append(seg.text.strip())

        return TranscriptionResult(
            text=" ".join(text_parts),
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            processing_time=time.time() - t0,
        )

    def transcribe_buffer(
        self,
        audio: np.ndarray,
        sr: int = 16000,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe a numpy audio buffer (for streaming)."""
        self.load_model()
        t0 = time.time()

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        segments_gen, info = self.model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=3,
            best_of=1,
            temperature=0.0,
            no_speech_threshold=0.9,
            condition_on_previous_text=False,
            word_timestamps=False,
            vad_filter=True,
        )

        segments: List[TranscriptionSegment] = []
        text_parts: List[str] = []
        for seg in segments_gen:
            segments.append(TranscriptionSegment(
                start=seg.start, end=seg.end, text=seg.text.strip(),
            ))
            text_parts.append(seg.text.strip())

        return TranscriptionResult(
            text=" ".join(text_parts),
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            processing_time=time.time() - t0,
        )

    def unload_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            logger.info("Whisper model unloaded")

    def __enter__(self):
        self.load_model()
        return self

    def __exit__(self, *exc):
        self.unload_model()
