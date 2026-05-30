"""Resolve studio/shorts scripts (verbatim vs LLM), optional BGM — patterns from Pixelle-Video / pyvideotrans."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.llm_service import LLMService
from app.utils.script_lang import lang_instruction, spoken_content_looks_wrong_lang
from app.utils.studio_script_format import (
    clean_llm_studio_output,
    extract_popups_from_text,
    normalize_studio_script_structure,
    script_needs_format_pass,
)

logger = logging.getLogger(__name__)


class ScriptService:
    @staticmethod
    def resolve_studio_script(raw_text: str, target_lang: str, use_raw_script: bool = True) -> str:
        text = normalize_studio_script_structure(raw_text)
        if not text:
            raise ValueError("Script is empty.")

        if use_raw_script:
            if spoken_content_looks_wrong_lang(text, target_lang):
                logger.warning(
                    "Studio: script language may not match target_lang=%s — TTS will sound wrong.",
                    target_lang,
                )
            logger.info("Studio: using submitted script (%d chars).", len(text))
            return text

        if not script_needs_format_pass(text) and len(extract_popups_from_text(text)) >= 2:
            if spoken_content_looks_wrong_lang(text, target_lang):
                logger.info("Studio: fixing script language for target_lang=%s.", target_lang)
            else:
                logger.info("Studio: script already has scenes + popups (%d chars).", len(text))
                return text

        try:
            polished = ScriptService._rewrite_and_enforce_language(text, target_lang)
            logger.info("Studio: AI rewrite (%d -> %d chars).", len(text), len(polished))
            return polished or text
        except Exception as exc:
            logger.warning("Studio AI rewrite skipped, using normalized script: %s", exc)
            return text

    @staticmethod
    def _rewrite_and_enforce_language(text: str, target_lang: str) -> str:
        rewritten = LLMService.rewrite_studio_script(text, target_lang)
        polished = normalize_studio_script_structure(clean_llm_studio_output(rewritten))
        if spoken_content_looks_wrong_lang(polished, target_lang):
            retry = (
                f"{lang_instruction(target_lang)}\n\n"
                "Rewrite the script below entirely in the target language (keep scene/popup markers):\n\n"
                f"{polished}"
            )
            polished = normalize_studio_script_structure(
                clean_llm_studio_output(LLMService.rewrite_studio_script(retry, target_lang))
            )
        return polished

    @staticmethod
    def rewrite_studio_script(raw_text: str, target_lang: str) -> str:
        """On-demand AI rewrite (Studio button) — not used during render unless text was replaced."""
        polished = ScriptService._rewrite_and_enforce_language(raw_text, target_lang)
        logger.info("Studio: AI rewrite (%d -> %d chars).", len(raw_text), len(polished))
        return polished

    @staticmethod
    def resolve_shorts_script(
        prompt: str,
        script: str,
        target_lang: str,
    ) -> str:
        cleaned_script = (script or "").strip()
        if cleaned_script:
            logger.info("Shorts: using verbatim script (%d chars).", len(cleaned_script))
            return cleaned_script

        cleaned_prompt = (prompt or "").strip()
        if not cleaned_prompt:
            raise ValueError("Shorts require either a prompt or a script.")

        logger.info("Shorts: generating script from prompt via LLM.")
        generated = LLMService.generate_short_script(cleaned_prompt, target_lang).strip()
        if not generated:
            raise ValueError("Script generation returned empty output.")
        return generated

    @staticmethod
    def resolve_bgm_path() -> Optional[Path]:
        """First audio file in storage/bgm/ (Pixelle-Video-style optional BGM)."""
        bgm_dir = settings.BGM_DIR
        if not settings.ENABLE_STUDIO_BGM or not bgm_dir.exists():
            return None
        for pattern in ("*.mp3", "*.wav", "*.m4a", "*.ogg"):
            matches = sorted(bgm_dir.glob(pattern))
            if matches:
                return matches[0]
        return None
