"""ElevenLabs TTS Provider — professional voice cloning with stability/similarity controls.

Requires ELEVENLABS_API_KEY in .env.
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


class ElevenLabsTTSProvider(TTSProviderBase):
    """ElevenLabs TTS with voice cloning and emotion control."""

    API_BASE = "https://api.elevenlabs.io/v1"

    @property
    def name(self) -> str:
        return "elevenlabs"

    def is_available(self) -> bool:
        return bool(getattr(settings, "ELEVENLABS_API_KEY", ""))

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_speed=True,
            supports_streaming=True,
            supports_voice_clone=True,
            supports_ssml=False,
            supports_emotion=True,
        )

    def list_voices(self) -> List[VoiceInfo]:
        # Return common built-in voices; full list requires API call
        return [
            VoiceInfo(id="21m00Tcm4TlvDq8ikWAM", name="Rachel", lang="en", gender="Female", provider="elevenlabs"),
            VoiceInfo(id="AZnzlk1XvdvUeBnXmlld", name="Domi", lang="en", gender="Female", provider="elevenlabs"),
            VoiceInfo(id="EXAVITQu4vr4xnSDxMaL", name="Bella", lang="en", gender="Female", provider="elevenlabs"),
            VoiceInfo(id="ErXwobaYiN019PkySvjV", name="Antoni", lang="en", gender="Male", provider="elevenlabs"),
            VoiceInfo(id="VR6AewLTigWG4xSOukaG", name="Arnold", lang="en", gender="Male", provider="elevenlabs"),
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
        api_key = getattr(settings, "ELEVENLABS_API_KEY", "")
        if not api_key:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        mp3_path = output_path.with_suffix(".mp3")

        voice_id = voice or "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel
        model_id = getattr(settings, "ELEVENLABS_MODEL", "eleven_multilingual_v2")

        try:
            url = f"{self.API_BASE}/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            payload = {
                "text": text[:5000],
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.85,
                    "style": 0.0,
                    "use_speaker_boost": True,
                    "speed": max(0.7, min(1.3, speed)),
                },
            }

            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            resp.raise_for_status()

            with open(mp3_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
            resp.close()

            if not mp3_path.exists() or mp3_path.stat().st_size == 0:
                return False

            success = self._convert_to_wav_24k_mono(mp3_path, output_path)
            mp3_path.unlink(missing_ok=True)
            return success

        except requests.HTTPError as e:
            if e.response and e.response.status_code in (401, 403, 429):
                logger.error("ElevenLabs auth/rate error (%d): %s", e.response.status_code, e)
            else:
                logger.error("ElevenLabs HTTP error: %s", e)
            return False
        except Exception as e:
            logger.error("ElevenLabs TTS failed: %s", e)
            mp3_path.unlink(missing_ok=True)
            return False
