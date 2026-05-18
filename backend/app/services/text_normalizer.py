"""
Vietnamese Text Normalizer Service for Dubify.

Wraps the third-party `vietnormalizer` library to preprocess translated text
BEFORE it is sent to TTS engines (Edge-TTS, Piper, F5-TTS).

Why this matters:
- TTS engines read "25/12/2023" literally instead of "ngày hai mươi lăm tháng mười hai..."
- Numbers like "50.000đ" become gibberish instead of "năm mươi nghìn đồng"
- English loanwords (container, server) get mispronounced instead of being transliterated
- Acronyms like "NASA", "GDP" are spelled letter-by-letter instead of being expanded

This service is automatically applied when target_lang is Vietnamese ("vi").
For other languages, text passes through unchanged (the library is Vietnamese-specific).
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Add the third-party vietnormalizer to the Python path
_VIETNORMALIZER_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "third_party" / "vietnormalizer"

_normalizer_instance = None
_init_attempted = False


def _get_normalizer():
    """Lazy-load the VietnameseNormalizer singleton. Returns None if unavailable."""
    global _normalizer_instance, _init_attempted

    if _init_attempted:
        return _normalizer_instance

    _init_attempted = True

    try:
        from vietnormalizer import VietnameseNormalizer

        _normalizer_instance = VietnameseNormalizer(enable_transliteration=True)
        logger.info(
            "VietnameseNormalizer loaded from PyPI (acronyms=%d, words=%d)",
            len(_normalizer_instance.acronym_map),
            len(_normalizer_instance.non_vietnamese_map),
        )
    except ImportError:
        try:
            vn_path = str(_VIETNORMALIZER_ROOT)
            if vn_path not in sys.path:
                sys.path.insert(0, vn_path)
            from vietnormalizer import VietnameseNormalizer

            _normalizer_instance = VietnameseNormalizer(enable_transliteration=True)
            logger.info("VietnameseNormalizer loaded from third_party/")
        except Exception as e:
            logger.warning("Could not load VietnameseNormalizer: %s", e)
            _normalizer_instance = None
    except Exception as e:
        logger.warning("Could not load VietnameseNormalizer: %s. TTS text will not be normalized.", e)
        _normalizer_instance = None

    return _normalizer_instance


def normalize_for_tts(text: str, target_lang: str = "vi") -> str:
    """
    Normalize text before sending to TTS.

    Only applies Vietnamese normalization when target_lang is "vi".
    For all other languages, text is returned as-is.

    Args:
        text: The translated text to normalize.
        target_lang: ISO 639-1 language code of the text.

    Returns:
        Normalized text ready for TTS consumption.
    """
    if not text or not text.strip():
        return text

    # Only normalize Vietnamese text
    if target_lang.lower() not in ("vi", "vie", "vie_latn"):
        return text

    normalizer = _get_normalizer()
    if normalizer is None:
        return text

    try:
        normalized = normalizer.normalize(text)
        if normalized != text.lower().strip():
            logger.debug("Normalized: '%s' → '%s'", text[:60], normalized[:60])
        return normalized
    except Exception as e:
        logger.error("Text normalization failed for '%s...': %s", text[:40], e)
        return text
