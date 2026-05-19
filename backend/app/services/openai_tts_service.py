"""OpenAI TTS provider — high-quality neural voices with streaming support."""

from __future__ import annotations

import logging
import asyncio
from pathlib import Path
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI TTS voices (alloy, echo, fable, onyx, nova, shimmer)
OPENAI_TTS_VOICES = {
    "alloy": "Neutral, balanced",
    "echo": "Warm, conversational male",
    "fable": "Expressive, British accent",
    "onyx": "Deep, authoritative male",
    "nova": "Friendly, upbeat female",
    "shimmer": "Clear, gentle female",
}


class OpenAITTSService:
    """Generate speech using OpenAI's TTS API (tts-1 or tts-1-hd)."""

    def __init__(
        self,
        voice: str = "nova",
        model: str = "tts-1",
        speed: float = 1.0,
        api_base: str = "",
    ):
        self.voice = voice if voice in OPENAI_TTS_VOICES else "nova"
        self.model = model if model in ("tts-1", "tts-1-hd") else "tts-1"
        self.speed = max(0.25, min(4.0, speed))
        self.api_base = (api_base or "https://api.openai.com/v1").rstrip("/")

    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate(self, text: str, output_path: Path) -> bool:
        """Generate audio from text using OpenAI TTS API with streaming."""
        if not self.is_available():
            logger.warning("OpenAI TTS: no API key configured.")
            return False

        if not text.strip():
            return False

        try:
            return await asyncio.to_thread(self._generate_sync, text, output_path)
        except Exception as e:
            logger.error("OpenAI TTS failed: %s", e)
            return False

    def _generate_sync(self, text: str, output_path: Path) -> bool:
        """Synchronous streaming download from OpenAI TTS API."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"{self.api_base}/audio/speech"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text[:4096],  # OpenAI limit
            "speed": self.speed,
            "response_format": "mp3",
        }

        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
        response.close()

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info("OpenAI TTS: generated %s (%d bytes)", output_path.name, output_path.stat().st_size)
            return True
        return False
