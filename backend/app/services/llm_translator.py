"""LLM-based Translation — context-aware translation using LLMs.

Requirement 15: Translate with surrounding context for better idiom/cultural adaptation.
Supports any LLM provider configured in Dubify (Groq, OpenAI, Gemini, Anthropic).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.core.config import settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class LLMTranslator:
    """Context-aware translation using LLM providers."""

    def __init__(
        self,
        target_lang: str = "vi",
        source_lang: str = "auto",
        style: str = "subtitle",  # subtitle, formal, casual
    ):
        self.target_lang = target_lang
        self.source_lang = source_lang
        self.style = style

    def is_available(self) -> bool:
        """Check if any LLM provider is configured."""
        return LLMService.llm_available()

    def translate_with_context(
        self,
        text: str,
        prev_context: str = "",
        next_context: str = "",
    ) -> str:
        """Translate a single segment with surrounding context.

        Args:
            text: The text to translate
            prev_context: Previous 1-2 segments for context
            next_context: Next 1-2 segments for context
        """
        if not text.strip():
            return text

        if not self.is_available():
            logger.warning("LLM translator unavailable — no API key configured.")
            return text

        style_instruction = {
            "subtitle": "Keep translations concise and natural for video subtitles. Max 2 lines.",
            "formal": "Use formal register appropriate for news/documentary.",
            "casual": "Use casual, conversational tone.",
        }.get(self.style, "")

        system_prompt = (
            f"You are a professional subtitle translator. "
            f"Translate the MAIN TEXT from {self.source_lang} to {self.target_lang}. "
            f"{style_instruction} "
            f"Preserve meaning, tone, and cultural nuance. "
            f"Output ONLY the translation — no explanations, no quotes, no labels."
        )

        user_content = ""
        if prev_context:
            user_content += f"[PREVIOUS CONTEXT]: {prev_context}\n"
        user_content += f"[MAIN TEXT TO TRANSLATE]: {text}\n"
        if next_context:
            user_content += f"[NEXT CONTEXT]: {next_context}\n"

        try:
            provider, api_key, model = LLMService._resolve_provider_and_model()
            if provider == "none" or not api_key:
                return text

            if provider == "groq":
                result = LLMService._call_groq(api_key, system_prompt, user_content, model=model)
            elif provider == "openai":
                result = LLMService._call_openai(api_key, system_prompt, user_content, model=model)
            elif provider == "gemini":
                result = LLMService._call_gemini(api_key, system_prompt, user_content, model=model)
            elif provider == "anthropic":
                result = LLMService._call_anthropic(api_key, system_prompt, user_content, model=model)
            else:
                return text

            # Clean up common LLM artifacts
            cleaned = result.strip().strip('"').strip("'")
            if cleaned and len(cleaned) < len(text) * 5:  # Sanity check
                return cleaned
            return text

        except Exception as e:
            logger.error("LLM translation failed: %s", e)
            return text

    def translate_batch_with_context(
        self,
        segments: List[dict],
        text_key: str = "text",
        max_context_chars: int = 200,
    ) -> List[dict]:
        """Translate a batch of segments with sliding context window.

        Each segment gets 2 surrounding segments as context.
        """
        results = []
        for i, seg in enumerate(segments):
            text = seg.get(text_key, "").strip()
            if not text:
                results.append({**seg, "translated_text": text})
                continue

            # Build context from surrounding segments
            prev_parts = []
            for j in range(max(0, i - 2), i):
                prev_parts.append(segments[j].get(text_key, ""))
            prev_context = " ".join(prev_parts)[-max_context_chars:]

            next_parts = []
            for j in range(i + 1, min(len(segments), i + 3)):
                next_parts.append(segments[j].get(text_key, ""))
            next_context = " ".join(next_parts)[:max_context_chars]

            translated = self.translate_with_context(text, prev_context, next_context)
            results.append({**seg, "translated_text": translated})

        return results
