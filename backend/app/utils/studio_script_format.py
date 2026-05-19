"""Normalize LLM studio scripts: scene headers, stat/def popups, TTS-safe body."""

from __future__ import annotations

import re

_STAT_DEF_RE = re.compile(r"\[(STAT|DEF):\s*([^\]]+)\]", re.IGNORECASE)
_STAT_DEF_BRACE_RE = re.compile(
    r"\{\{(stat|def):\s*([^}]+)\}\}",
    re.IGNORECASE,
)
_INLINE_SECTION_RE = re.compile(
    r"\[(Hook|Story|Insight|Close|Mở đầu|Kết|Cảnh\s*\d+|Scene\s*\d+|[A-Za-zÀ-ỹ][^\]]{0,48})\]\s*",
    re.IGNORECASE,
)
_SCENE_PREFIX_RE = re.compile(
    r"(?:^|[\n.!?…\]]\s*)(Scene\s*(\d+)\s*:)\s*",
    re.IGNORECASE | re.MULTILINE,
)
_SECTION_LINE_RE = re.compile(r"^\s*\[[^\]]+\]\s*$", re.MULTILINE)


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


def normalize_studio_script_structure(text: str) -> str:
    """Turn run-on LLM scripts into [Section] blocks + line-broken popups."""
    t = clean_llm_studio_output(text)

    def _scene_repl(match: re.Match[str]) -> str:
        num = match.group(2) or "1"
        return f"\n[Cảnh {num}]\n"

    t = _SCENE_PREFIX_RE.sub(_scene_repl, t)
    t = _INLINE_SECTION_RE.sub(lambda m: f"\n[{m.group(1).strip()}]\n", t)
    t = re.sub(r"\s*(\[(?:STAT|DEF):)", r"\n\1", t, flags=re.IGNORECASE)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def script_needs_format_pass(text: str) -> bool:
    """True when the script is still a flat blob (inline Hook / Scene N:)."""
    cleaned = (text or "").strip()
    if len(cleaned) < 80:
        return False
    if re.search(r"Scene\s*\d+\s*:", cleaned, re.IGNORECASE):
        return True
    if re.search(r"\[(?:Hook|STAT|DEF)[^\]]*\].{50,}", cleaned, re.IGNORECASE):
        return True
    section_lines = len(_SECTION_LINE_RE.findall(cleaned))
    return section_lines < 2 and len(cleaned) > 200


def strip_section_markers_for_tts(text: str) -> str:
    """Remove scene headers so TTS does not say Hook / Scene 1 / etc."""
    without = re.sub(r"^\s*\[[^\]]+\]\s*$", "", text or "", flags=re.MULTILINE)
    without = re.sub(r"\[(?!STAT:|DEF:)([^\]]{1,60})\]\s*", "", without, flags=re.IGNORECASE)
    without = re.sub(r"(?:^|\s)Scene\s*\d+\s*:\s*", " ", without, flags=re.IGNORECASE | re.MULTILINE)
    without = re.sub(r"\s+", " ", without)
    return without.strip()


def strip_popup_markers_for_tts(text: str) -> str:
    """Remove [STAT: ...] / [DEF: ...] so TTS does not read labels aloud."""
    # Remove complete markers: [STAT: xxx] and [DEF: xxx]
    without = _STAT_DEF_RE.sub("", text or "")
    # Also remove partial/malformed markers that regex might miss
    without = re.sub(r"\[STAT:[^\]]*\]?", "", without, flags=re.IGNORECASE)
    without = re.sub(r"\[DEF:[^\]]*\]?", "", without, flags=re.IGNORECASE)
    # Remove any remaining "STAT:" or "DEF:" prefixes (after bracket stripping)
    without = re.sub(r"(?:^|\s)(?:STAT|DEF)\s*:\s*", " ", without, flags=re.IGNORECASE)
    # Strip section markers
    without = strip_section_markers_for_tts(without)
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


_GENERIC_SCENE_TITLE = re.compile(
    r"^(hook|story|insight|close|mở đầu|kết|kết luận|cảnh\s*\d+|scene\s*\d+)$",
    re.IGNORECASE,
)


def scene_visual_title(title: str) -> str:
    """Hide meta labels like [Hook] from on-screen scene cards."""
    cleaned = (title or "").strip()
    if not cleaned or _GENERIC_SCENE_TITLE.match(cleaned):
        return ""
    return cleaned


def schedule_popup_timings(
    popups: list[dict[str, str]],
    total_duration: float,
    *,
    show_seconds: float = 4.5,
) -> list[tuple[float, float, dict[str, str]]]:
    """Spread stat/def overlays across the voiceover timeline with visual impact."""
    if not popups or total_duration <= 0.5:
        return []

    scheduled: list[tuple[float, float, dict[str, str]]] = []
    # Distribute popups evenly but avoid first 0.8s and last 0.3s
    usable_start = 0.8
    usable_end = total_duration - 0.3
    usable_range = max(usable_end - usable_start, 1.0)
    slot = usable_range / (len(popups) + 1)
    
    for index, popup in enumerate(popups):
        start = usable_start + slot * (index + 1) - show_seconds * 0.2
        start = max(usable_start, start)
        end = min(usable_end, start + show_seconds)
        if end <= start + 0.5:
            end = min(total_duration, start + 2.0)
        scheduled.append((start, end, popup))
    return scheduled
