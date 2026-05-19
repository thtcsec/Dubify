"""TTS Provider Registry — capability-based routing without provider-specific conditionals."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.services.tts_providers.base import TTSProviderBase, ProviderCapabilities

logger = logging.getLogger(__name__)

# Global registry
_providers: Dict[str, TTSProviderBase] = {}


def register(provider: TTSProviderBase) -> None:
    """Register a TTS provider instance."""
    _providers[provider.name] = provider
    logger.debug("TTS provider registered: %s", provider.name)


def get_provider(name: str) -> Optional[TTSProviderBase]:
    """Get a provider by name."""
    return _providers.get(name)


def list_providers() -> List[TTSProviderBase]:
    """List all registered providers."""
    return list(_providers.values())


def find_available(
    *,
    require_speed: bool = False,
    require_clone: bool = False,
    require_streaming: bool = False,
    fallback_chain: Optional[List[str]] = None,
) -> Optional[TTSProviderBase]:
    """Find the first available provider matching required capabilities.

    If fallback_chain is provided, try providers in that order.
    Otherwise, iterate all registered providers.
    """
    candidates = (
        [_providers[n] for n in fallback_chain if n in _providers]
        if fallback_chain
        else list(_providers.values())
    )

    for provider in candidates:
        if not provider.is_available():
            continue
        caps = provider.capabilities()
        if require_speed and not caps.supports_speed:
            continue
        if require_clone and not caps.supports_voice_clone:
            continue
        if require_streaming and not caps.supports_streaming:
            continue
        return provider

    return None


# Convenience alias
tts_registry = type("TTSRegistry", (), {
    "register": staticmethod(register),
    "get": staticmethod(get_provider),
    "list": staticmethod(list_providers),
    "find_available": staticmethod(find_available),
})()
