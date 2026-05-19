"""Punctuation Restoration — add missing punctuation to raw ASR output.

Requirement 16: Improve subtitle readability by restoring punctuation.
Uses a simple rule-based approach + optional modelscope model.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PunctuationRestorer:
    """Restore punctuation in ASR transcript output."""

    def __init__(self, use_model: bool = True):
        self.use_model = use_model
        self._model = None
        self._model_checked = False

    def is_available(self) -> bool:
        """Check if the punctuation model is loadable."""
        if not self.use_model:
            return True  # Rule-based always available
        if self._model_checked:
            return self._model is not None
        self._model_checked = True
        try:
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks
            self._model = pipeline(
                task=Tasks.punctuation,
                model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
                model_revision="v2.0.4",
                disable_update=True,
                disable_progress_bar=True,
                disable_log=True,
            )
            return True
        except Exception as e:
            logger.warning("Punctuation model unavailable: %s. Using rule-based fallback.", e)
            self._model = None
            return True  # Rule-based still works

    def restore(self, text: str, lang: str = "auto") -> str:
        """Restore punctuation in text.

        Preserves original meaning, adds periods/commas/question marks.
        """
        if not text or not text.strip():
            return text

        # Try model-based restoration first
        if self.use_model and self._model is not None:
            try:
                result = self._model(text)
                if isinstance(result, dict) and "text" in result:
                    return result["text"]
                if isinstance(result, list) and result:
                    return result[0].get("text", text)
            except Exception as e:
                logger.warning("Model punctuation failed, using rules: %s", e)

        # Rule-based fallback
        return self._rule_based_restore(text, lang)

    def restore_segments(self, segments: List[Dict], text_key: str = "text") -> List[Dict]:
        """Restore punctuation for a list of ASR segments.

        Preserves timestamps and other segment metadata.
        """
        results = []
        for seg in segments:
            text = seg.get(text_key, "")
            restored = self.restore(text)
            results.append({**seg, text_key: restored})
        return results

    @staticmethod
    def _rule_based_restore(text: str, lang: str = "auto") -> str:
        """Simple rule-based punctuation restoration."""
        if not text.strip():
            return text

        # Already has punctuation? Skip.
        if re.search(r"[.!?,;:。！？，；：]", text):
            return text

        sentences = re.split(r"\s{2,}|\n+", text.strip())
        restored_parts = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Add period at end if missing
            if sentence and sentence[-1] not in ".!?。！？…":
                # Detect questions
                question_words = (
                    r"\b(what|who|where|when|why|how|is|are|do|does|did|can|could|would|should)\b"
                    if lang in ("en", "auto")
                    else r"(gì|nào|sao|không|chưa|đâu|bao giờ|ai|mấy)"
                )
                if re.search(question_words, sentence, re.IGNORECASE):
                    sentence += "?"
                else:
                    sentence += "."

            # Capitalize first letter (for Latin scripts)
            if sentence and sentence[0].isalpha() and sentence[0].islower():
                sentence = sentence[0].upper() + sentence[1:]

            restored_parts.append(sentence)

        return " ".join(restored_parts)
