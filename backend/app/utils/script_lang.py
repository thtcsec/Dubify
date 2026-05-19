"""Language checks for studio/research scripts (TTS must match target_lang)."""

from __future__ import annotations

import re

from app.utils.studio_script_format import strip_popup_markers_for_tts

_EN_STOPWORDS = re.compile(
    r"\b(the|and|is|are|was|were|with|for|this|that|from|have|has|had|"
    r"developers|conference|technology|google|android|will|can|you|your)\b",
    re.IGNORECASE,
)
_VI_DIACRITICS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổễơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)


def lang_instruction(target_lang: str) -> str:
    code = (target_lang or "vi").split("-")[0].lower()
    if code == "vi":
        return (
            "Vietnamese (tiếng Việt) ONLY — every spoken sentence must be in Vietnamese. "
            "Do not write English narration."
        )
    if code == "en":
        return "English ONLY — do not mix Vietnamese in spoken lines."
    return f"Language code {code} ONLY for all spoken lines."


def spoken_content_looks_wrong_lang(text: str, target_lang: str) -> bool:
    """Heuristic: English body when user asked for Vietnamese TTS."""
    spoken = strip_popup_markers_for_tts(text or "")
    if len(spoken) < 40:
        return False

    code = (target_lang or "vi").split("-")[0].lower()
    if code != "vi":
        return False

    if _VI_DIACRITICS.search(spoken):
        return False

    words = spoken.split()
    if len(words) < 12:
        return False

    en_hits = len(_EN_STOPWORDS.findall(spoken))
    return en_hits >= 4 or en_hits / max(len(words), 1) > 0.08
