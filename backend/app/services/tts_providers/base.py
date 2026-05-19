"""Abstract TTS Provider Interface with declarative capabilities.

All TTS providers implement this contract. Adding a new provider requires:
1. Create a class implementing TTSProviderBase
2. Register it in the registry

No changes to pipeline, API, or UI code needed.
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declarative capability descriptor for TTS providers."""

    supports_streaming: bool = False
    supports_voice_clone: bool = False
    supports_ssml: bool = False
    supports_speed: bool = False
    supports_emotion: bool = False


@dataclass
class VoiceInfo:
    """Voice metadata returned by providers."""

    id: str
    name: str
    lang: str
    gender: str = "Unknown"
    provider: str = ""
    preview_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class TTSProviderBase(ABC):
    """Abstract base class for all TTS providers.

    Contract:
    - synthesize() produces WAV (16-bit PCM, 24kHz, mono) at output_path
    - is_available() returns False if provider cannot serve requests (missing key, server down)
    - capabilities() returns static ProviderCapabilities
    - list_voices() returns available voices for this provider
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'edge', 'openai', 'kokoro')."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider can serve requests right now."""
        ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return static capability flags."""
        ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        *,
        speed: float = 1.0,
        ref_audio: Optional[Path] = None,
        ref_text: Optional[str] = None,
    ) -> bool:
        """Generate audio file. Returns True on success.

        Output MUST be WAV 16-bit PCM, 24kHz, mono.
        Providers generating other formats must convert internally.
        """
        ...

    def list_voices(self) -> List[VoiceInfo]:
        """Return available voices. Override for dynamic voice lists."""
        return []

    # ─── Shared Utilities ────────────────────────────────────────────────

    @staticmethod
    def _convert_to_wav_24k_mono(input_path: Path, output_path: Path) -> bool:
        """Convert any audio file to WAV 16-bit PCM, 24kHz, mono."""
        if input_path == output_path:
            tmp = output_path.with_suffix(".tmp.wav")
        else:
            tmp = output_path

        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(input_path),
                "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                str(tmp),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if tmp != output_path:
                tmp.replace(output_path)
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as e:
            logger.error("WAV conversion failed: %s", e)
            return False
