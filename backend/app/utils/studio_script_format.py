"""Normalize LLM studio scripts: scene headers, stat/def popups, TTS-safe body."""

from __future__ import annotations

import re

_STAT_DEF_RE = re.compile(r"\[(STAT|DEF):\s*([^\]]+)\]", re.IGNORECASE)
_STAT_DEF_BRACE_RE = re.compile(
    r"\{\{(stat|def):\s*([^}]+)\}\}",
    re.IGNORECASE,
)


def normalize_popup_markers(text: str) -> str:
    """Convert {{stat: x}} → [STAT: x] for consistent parsing."""
    out = _STAT_DEF_BRACE_RE.sub(
        lambda m: f"[{m.group(1).upper()}: {m.group(2).strip()}]",
        text or "",
    )
    return out


def clean_llm_studio_output(text: str) -> str:
    """Strip markdown/URLs/junk; keep scene + popup markers."""
    cleaned = normalize_popup_markers(text or "")
    cleaned = cleaned.replace("\r\n", "\n")
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def strip_popup_markers_for_tts(text: str) -> str:
    """Remove [STAT: ...] / [DEF: ...] so TTS does not read labels aloud."""
    without = _STAT_DEF_RE.sub("", text or "")
    without = re.sub(r"\s+", " ", without)
    return without.strip()


def extract_popups_from_text(text: str) -> list[dict[str, str]]:
    """Parse popup markers for preview/export metadata."""
    items: list[dict[str, str]] = []
    for match in _STAT_DEF_RE.finditer(text or ""):
        kind = match.group(1).upper()
        body = match.group(2).strip()
        items.append({"type": "stat" if kind == "STAT" else "def", "text": body})
    return items
