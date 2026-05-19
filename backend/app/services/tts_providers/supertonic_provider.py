"""Supertonic TTS Provider — lightning-fast, on-device, 31-language TTS via ONNX.

Supertonic 3 from Supertone Inc (MIT license).
- 99M parameters, 44.1kHz output, runs on CPU
- 31 languages including Vietnamese
- Expression tags: <laugh>, <breath>, <sigh>, etc.
- Voice Builder for custom voices
- OpenAI-compatible HTTP server via `supertonic serve`

Setup:
    pip install 'supertonic[serve]'
    supertonic serve --host 127.0.0.1 --port 7788

Or use directly via Python SDK (no server needed):
    pip install supertonic
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

# Supertonic built-in voices
SUPERTONIC_VOICES = [
    VoiceInfo(id="M1", name="Male 1 (Default)", lang="multi", gender="Male", provider="supertonic"),
    VoiceInfo(id="M2", name="Male 2", lang="multi", gender="Male", provider="supertonic"),
    VoiceInfo(id="M3", name="Male 3", lang="multi", gender="Male", provider="supertonic"),
    VoiceInfo(id="M4", name="Male 4", lang="multi", gender="Male", provider="supertonic"),
    VoiceInfo(id="M5", name="Male 5", lang="multi", gender="Male", provider="supertonic"),
    VoiceInfo(id="F1", name="Female 1", lang="multi", gender="Female", provider="supertonic"),
    VoiceInfo(id="F2", name="Female 2", lang="multi", gender="Female", provider="supertonic"),
    VoiceInfo(id="F3", name="Female 3", lang="multi", gender="Female", provider="supertonic"),
    VoiceInfo(id="F4", name="Female 4", lang="multi", gender="Female", provider="supertonic"),
    VoiceInfo(id="F5", name="Female 5", lang="multi", gender="Female", provider="supertonic"),
]

# Expression tags that Supertonic 3 supports
EXPRESSION_TAGS = ["<laugh>", "<breath>", "<sigh>", "<cough>", "<hmm>", "<gasp>", "<groan>", "<yawn>", "<whisper>", "<shout>"]


class SupertonicTTSProvider(TTSProviderBase):
    """Supertonic TTS — on-device, 31-language, expression-aware.

    Can run in two modes:
    1. HTTP server mode (supertonic serve) — uses /v1/audio/speech endpoint
    2. Direct Python SDK mode — imports supertonic package directly
    """

    @property
    def name(self) -> str:
        return "supertonic"

    def is_available(self) -> bool:
        """Check if Supertonic is available (server or SDK)."""
        # Try HTTP server first
        url = self._server_url()
        if url:
            try:
                resp = requests.get(f"{url}/", timeout=2)
                return resp.status_code < 500
            except Exception:
                pass

        # Try direct SDK
        try:
            import supertonic  # noqa: F401
            return True
        except ImportError:
            return False

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_speed=True,
            supports_streaming=False,
            supports_voice_clone=True,  # Via Voice Builder JSON
            supports_ssml=False,
            supports_emotion=True,  # Expression tags
        )

    def list_voices(self) -> List[VoiceInfo]:
        return SUPERTONIC_VOICES

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

        # Try HTTP server mode first (faster for repeated calls)
        url = self._server_url()
        if url:
            return await asyncio.to_thread(
                self._synthesize_http, text, voice, output_path, speed, url
            )

        # Fallback to direct SDK
        return await asyncio.to_thread(
            self._synthesize_sdk, text, voice, output_path, speed
        )

    def _synthesize_http(self, text: str, voice: str, output_path: Path, speed: float, base_url: str) -> bool:
        """Synthesize via Supertonic HTTP server (OpenAI-compatible endpoint)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = output_path.with_suffix(".wav")

        try:
            url = f"{base_url}/v1/audio/speech"
            payload = {
                "input": text[:4096],
                "voice": voice or "M1",
                "speed": max(0.7, min(2.0, speed)),
                "response_format": "wav",
            }

            # Add language hint if detectable
            lang = self._detect_lang_hint(text)
            if lang:
                payload["lang"] = lang

            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()

            with open(wav_path, "wb") as f:
                f.write(resp.content)

            if not wav_path.exists() or wav_path.stat().st_size == 0:
                return False

            # Supertonic outputs 44.1kHz — convert to standard 24kHz mono
            success = self._convert_to_wav_24k_mono(wav_path, output_path)
            if wav_path != output_path:
                wav_path.unlink(missing_ok=True)
            return success

        except Exception as e:
            logger.error("Supertonic HTTP synthesis failed: %s", e)
            wav_path.unlink(missing_ok=True)
            return False

    def _synthesize_sdk(self, text: str, voice: str, output_path: Path, speed: float) -> bool:
        """Synthesize directly via Supertonic Python SDK."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = output_path.with_suffix(".st.wav")

        try:
            from supertonic import TTS

            tts = TTS(auto_download=True)
            style = tts.get_voice_style(voice_name=voice or "M1")

            # Detect language
            lang = self._detect_lang_hint(text) or "na"  # "na" = language-agnostic

            wav, duration = tts.synthesize(
                text=text[:4096],
                lang=lang,
                voice_style=style,
                total_steps=8,  # Medium quality (5=low, 12=high)
                speed=max(0.7, min(2.0, speed)),
            )

            tts.save_audio(wav, str(wav_path))

            if not wav_path.exists() or wav_path.stat().st_size == 0:
                return False

            # Convert 44.1kHz to 24kHz mono
            success = self._convert_to_wav_24k_mono(wav_path, output_path)
            wav_path.unlink(missing_ok=True)
            return success

        except ImportError:
            logger.error("Supertonic SDK not installed. Run: pip install supertonic")
            return False
        except Exception as e:
            logger.error("Supertonic SDK synthesis failed: %s", e)
            wav_path.unlink(missing_ok=True)
            return False

    @staticmethod
    def _server_url() -> str:
        """Get Supertonic server URL from config."""
        url = getattr(settings, "SUPERTONIC_API_URL", "").strip()
        return url.rstrip("/") if url else ""

    @staticmethod
    def _detect_lang_hint(text: str) -> str:
        """Simple language detection for Supertonic lang parameter."""
        # Vietnamese detection (diacritics)
        if any(c in text for c in "ăâđêôơưắấ"):
            return "vi"
        # Japanese (hiragana/katakana)
        if any("\u3040" <= c <= "\u30ff" for c in text):
            return "ja"
        # Korean (hangul)
        if any("\uac00" <= c <= "\ud7af" for c in text):
            return "ko"
        # Chinese (CJK unified)
        if any("\u4e00" <= c <= "\u9fff" for c in text):
            return "zh"
        # Default: let Supertonic auto-detect
        return "na"
