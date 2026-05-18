"""Dubbing mode and TTS voice selection tests."""

from app.core.config import settings
from app.services.tts_service import TTSService


def test_hybrid_uses_google_translate():
    settings.PROCESSING_ENGINE = "local"
    settings.PROCESSING_MODE = "hybrid"
    assert settings.default_translation_service() == "google"
    assert settings.allow_network_tts() is True


def test_offline_uses_nllb():
    settings.PROCESSING_ENGINE = "local"
    settings.PROCESSING_MODE = "offline"
    assert settings.default_translation_service() == "nllb"
    assert settings.allow_network_tts() is False


def test_default_voice_for_english():
    assert TTSService.default_voice_for_lang("en").startswith("en-")


def test_default_voice_for_vietnamese():
    assert TTSService.default_voice_for_lang("vi").startswith("vi-")
