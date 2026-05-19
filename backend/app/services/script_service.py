"""Resolve studio/shorts scripts (verbatim vs LLM), optional BGM — patterns from Pixelle-Video / pyvideotrans."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ScriptService:
    @staticmethod
    def resolve_studio_script(raw_text: str, target_lang: str, use_raw_script: bool = True) -> str:
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("Script is empty.")

        logger.info("Studio: using submitted script (%d chars).", len(text))
        return text

    @staticmethod
    def rewrite_studio_script(raw_text: str, target_lang: str) -> str:
        """On-demand AI rewrite (Studio button) — not used during render unless text was replaced."""
        rewritten = LLMService.rewrite_studio_script(raw_text, target_lang)
        logger.info("Studio: AI rewrite (%d -> %d chars).", len(raw_text), len(rewritten))
        return rewritten

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
