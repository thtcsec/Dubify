"""DeepL translation provider — highest quality machine translation for European languages."""

from __future__ import annotations

import logging
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

# DeepL supported target languages
DEEPL_LANG_MAP = {
    "en": "EN-US",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pt": "PT-BR",
    "ru": "RU",
    "ja": "JA",
    "ko": "KO",
    "zh": "ZH-HANS",
    "ar": "AR",
    "id": "ID",
    "nl": "NL",
    "pl": "PL",
    "tr": "TR",
    "uk": "UK",
    "vi": "VI",  # DeepL added Vietnamese support
}


class DeepLService:
    """Translate text using DeepL API (Free or Pro)."""

    def __init__(self, target_lang: str = "vi"):
        self.target_lang = target_lang
        self.api_key = settings.DEEPL_API_KEY
        # DeepL Free uses api-free.deepl.com, Pro uses api.deepl.com
        if self.api_key and ":fx" in self.api_key:
            self.api_base = "https://api-free.deepl.com/v2"
        else:
            self.api_base = "https://api.deepl.com/v2"

    def is_available(self) -> bool:
        return bool(self.api_key) and self.target_lang.lower() in DEEPL_LANG_MAP

    def translate(self, text: str, source_lang: Optional[str] = None) -> str:
        """Translate a single text string."""
        if not text.strip() or not self.is_available():
            return text

        target_code = DEEPL_LANG_MAP.get(self.target_lang.lower(), "EN-US")

        try:
            response = requests.post(
                f"{self.api_base}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={
                    "text": text,
                    "target_lang": target_code,
                    **({"source_lang": source_lang.upper()[:2]} if source_lang and source_lang != "auto" else {}),
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            translations = result.get("translations", [])
            if translations:
                return translations[0].get("text", text)
            return text
        except Exception as e:
            logger.error("DeepL translation failed: %s", e)
            return text
