"""Word-level cues for TikTok-style highlight-as-spoken subtitles."""

from __future__ import annotations

import re


def expand_cues_to_words(
    cues: list[tuple[float, float, str]],
) -> list[tuple[float, float, str]]:
    """Split each subtitle cue into per-word timed segments."""
    word_cues: list[tuple[float, float, str]] = []
    for start, end, text in cues:
        cleaned = re.sub(r"\s+", " ", (text or "").strip())
        if not cleaned:
            continue
        words = cleaned.split(" ")
        if not words:
            continue
        span = max(end - start, 0.05)
        step = span / len(words)
        cursor = start
        for word in words:
            word_end = min(cursor + step, end)
            word_cues.append((cursor, max(word_end, cursor + 0.03), word))
            cursor = word_end
    return word_cues


def group_words_into_lines(
    word_cues: list[tuple[float, float, str]],
    *,
    max_words: int = 7,
) -> list[list[tuple[float, float, str]]]:
    """Batch word cues into display lines."""
    if not word_cues:
        return []
    lines: list[list[tuple[float, float, str]]] = []
    batch: list[tuple[float, float, str]] = []
    for cue in word_cues:
        batch.append(cue)
        if len(batch) >= max_words:
            lines.append(batch)
            batch = []
    if batch:
        lines.append(batch)
    return lines
