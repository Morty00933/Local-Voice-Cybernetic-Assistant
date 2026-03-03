"""Audio preprocessor: normalization, resampling, speech extraction."""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000


@dataclass
class SpeechSegment:
    start: float  # seconds
    end: float    # seconds


class AudioPreprocessor:
    """Audio preprocessor for the STT pipeline.

    - Resampling to 16 kHz mono
    - Peak normalization
    - Optional VAD-based silence removal
    """

    def __init__(self, vad_threshold: float = 0.5):
        self.vad_threshold = vad_threshold
        self._vad_model = None
        self._get_speech_ts = None

    # ------------------------------------------------------------------
    # VAD (lazy-loaded)
    # ------------------------------------------------------------------
    def _load_vad(self) -> None:
        if self._vad_model is not None:
            return
        import torch
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        self._vad_model = model
        self._get_speech_ts = utils[0]
        logger.info("Silero VAD loaded")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        import librosa
        audio, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE, mono=True)
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        return audio, sr

    def load_buffer(self, raw_bytes: bytes, sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
        """Convert raw PCM int16 bytes to float32 numpy array."""
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    def normalize(self, audio: np.ndarray) -> np.ndarray:
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio / peak * 0.95
        return audio

    def detect_speech(
        self,
        audio: np.ndarray,
        sr: int = TARGET_SAMPLE_RATE,
        min_speech_ms: int = 250,
        min_silence_ms: int = 100,
    ) -> List[SpeechSegment]:
        import torch
        self._load_vad()
        ts = self._get_speech_ts(
            torch.tensor(audio),
            self._vad_model,
            sampling_rate=sr,
            threshold=self.vad_threshold,
            min_speech_duration_ms=min_speech_ms,
            min_silence_duration_ms=min_silence_ms,
            speech_pad_ms=400,
            return_seconds=True,
        )
        return [SpeechSegment(start=t["start"], end=t["end"]) for t in ts]

    def extract_speech(
        self,
        audio: np.ndarray,
        segments: List[SpeechSegment],
        sr: int = TARGET_SAMPLE_RATE,
        padding_ms: int = 200,
    ) -> np.ndarray:
        if not segments:
            return audio
        pad = int(padding_ms * sr / 1000)
        parts = []
        for seg in segments:
            s = max(0, int(seg.start * sr) - pad)
            e = min(len(audio), int(seg.end * sr) + pad)
            parts.append(audio[s:e])
        return np.concatenate(parts) if parts else audio

    def preprocess(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        remove_silence: bool = False,
        normalize: bool = True,
    ) -> str:
        """Full preprocessing pipeline. Returns path to preprocessed WAV."""
        import soundfile as sf

        audio, sr = self.load_audio(audio_path)

        if normalize:
            audio = self.normalize(audio)

        if remove_silence:
            segs = self.detect_speech(audio, sr)
            if segs:
                audio = self.extract_speech(audio, segs, sr)

        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="preprocessed_")
            os.close(fd)

        sf.write(output_path, audio, sr)
        return output_path

    def preprocess_buffer(
        self,
        audio: np.ndarray,
        sr: int = TARGET_SAMPLE_RATE,
        normalize: bool = True,
    ) -> np.ndarray:
        """Preprocess an in-memory audio buffer."""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if normalize:
            audio = self.normalize(audio)
        return audio
