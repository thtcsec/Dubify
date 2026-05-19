"""Kokoro TTS Provider — local OpenAI-compatible TTS API (high quality offline).

Requires a running Kokoro TTS server (e.g. kokoro-onnx or AllTalk).
Configure KOKORO_API_URL in .env (default: http://localhost:8880).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import requests

from app.core.config import settings
from app.services.tts_providers.base import (
    TTSProviderBase,
    ProviderCapabilities,
    VoiceInfo,
)

logger = logging.getLogger(__name__)


class KokoroTTSProvider(TTSProviderBase):
    """Local Kokoro TTS via OpenAI-compatible /v1/audio/speech endpoint."""

    @property
    def name(self) -> str:
        return "kokoro"

    def is_available(self) -> bool:
        url = self._api_url()
        if not url:
            return False
        try:
            # Quick health check — just verify server responds
            resp = requests.get(url.replace("/v1/audio/speech", "/"), timeout=3)
            return resp.status_code < 500
        except Exception:
            return False

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_speed=True,
            supports_streaming=False,
            supports_voice_clone=False,
            supports_ssml=False,
            supports_emotion=False,
        )

    def list_voices(self) -> List[VoiceInfo]:
        # Kokoro voices depend on the server config — return common defaults
        return [
            VoiceInfo(id="af_heart", name="Heart (Female)", lang="en", gender="Female", provider="kokoro"),
            VoiceInfo(id="af_bella", name="Bella (Female)", lang="en", gender="Female", provider="kokoro"),
            VoiceInfo(id="am_adam", name="Adam (Male)", lang="en", gender="Male", provider="kokoro"),
            VoiceInfo(id="am_michael", name="Michael (Male)", lang="en", gender="Male", provider="kokoro"),
        ]

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
        if not text.strip():
            return False

        return await asyncio.to_thread(self._synthesize_sync, text, voice, output_path, speed)

    def _synthesize_sync(self, text: str, voice: str, output_path: Path, speed: float) -> bool:
        url = self._api_url()
        if not url:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        mp3_path = output_path.with_suffix(".mp3")

        try:
            payload = {
                "input": text[:4096],
                "voice": voice or "af_heart",
                "speed": max(0.5, min(2.0, speed)),
            }
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()

            with open(mp3_path, "wb") as f:
                f.write(resp.content)

            if not mp3_path.exists() or mp3_path.stat().st_size == 0:
                return False

            # Convert to standard WAV format
            success = self._convert_to_wav_24k_mono(mp3_path, output_path)
            mp3_path.unlink(missing_ok=True)
            return success

        except Exception as e:
            logger.error("Kokoro TTS failed: %s", e)
            mp3_path.unlink(missing_ok=True)
            return False

    @staticmethod
    def _api_url() -> str:
        base = getattr(settings, "KOKORO_API_URL", "").strip()
        if not base:
            return ""
        base = base.rstrip("/")
        if not base.endswith("/v1/audio/speech"):
            base += "/v1/audio/speech"
        return base
