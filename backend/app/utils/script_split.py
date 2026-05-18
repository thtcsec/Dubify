"""Split spoken scripts into caption-friendly chunks (sentence-first, inspired by Pixelle-Video)."""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")


def split_spoken_lines(text: str, max_chars: int = 120) -> list[str]:
    """Split script into lines for subtitles / TTS chunking."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    sentences: list[str] = []
    for block in _SENTENCE_END.split(cleaned):
        part = block.strip()
        if part:
            sentences.append(part)

    if not sentences:
        sentences = [cleaned]

    lines: list[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            lines.append(sentence)
            continue
        words = sentence.split()
        chunk: list[str] = []
        length = 0
        for word in words:
            extra = len(word) + (1 if chunk else 0)
            if chunk and length + extra > max_chars:
                lines.append(" ".join(chunk))
                chunk = [word]
                length = len(word)
            else:
                chunk.append(word)
                length += extra
        if chunk:
            lines.append(" ".join(chunk))
    return lines
