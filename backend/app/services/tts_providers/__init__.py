"""TTS Provider Interface — all providers implement this contract."""

from app.services.tts_providers.base import TTSProviderBase, ProviderCapabilities, VoiceInfo
from app.services.tts_providers.registry import tts_registry, get_provider, list_providers

__all__ = [
    "TTSProviderBase",
    "ProviderCapabilities",
    "VoiceInfo",
    "tts_registry",
    "get_provider",
    "list_providers",
]
