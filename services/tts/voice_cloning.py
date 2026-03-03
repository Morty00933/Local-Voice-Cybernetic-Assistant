"""Voice cloning: manage reference speaker WAV files."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from shared.config import settings

logger = logging.getLogger(__name__)

DEFAULT_VOICES_DIR = "/voices"


class VoiceManager:
    """Manages reference speaker WAV files for voice cloning."""

    def __init__(self, voices_dir: str | None = None):
        self.voices_dir = Path(voices_dir or os.environ.get("VOICES_DIR", DEFAULT_VOICES_DIR))
        self.voices_dir.mkdir(parents=True, exist_ok=True)

    def list_voices(self) -> list[str]:
        """List available voice names."""
        return sorted(
            p.stem for p in self.voices_dir.glob("*.wav")
        )

    def get_voice_path(self, name: str) -> Optional[str]:
        """Get path to a reference WAV by name."""
        wav = self.voices_dir / f"{name}.wav"
        if wav.exists():
            return str(wav)
        return None

    def add_voice(self, name: str, wav_path: str) -> str:
        """Copy a WAV file as a named voice reference."""
        dest = self.voices_dir / f"{name}.wav"
        shutil.copy2(wav_path, dest)
        logger.info("Added voice '%s' from %s", name, wav_path)
        return str(dest)

    def remove_voice(self, name: str) -> bool:
        """Remove a voice reference."""
        wav = self.voices_dir / f"{name}.wav"
        if wav.exists():
            wav.unlink()
            logger.info("Removed voice '%s'", name)
            return True
        return False

    def get_default_voice(self) -> Optional[str]:
        """Get path to the default reference voice."""
        default = self.get_voice_path("default")
        if default:
            return default
        voices = self.list_voices()
        if voices:
            return self.get_voice_path(voices[0])
        return None
