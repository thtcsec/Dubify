import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS_PER_LINE = 42
DEFAULT_MAX_SUBTITLE_LINES = 2


def wrap_subtitle_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS_PER_LINE,
    max_lines: int = DEFAULT_MAX_SUBTITLE_LINES,
) -> str:
    """Break long subtitle lines for on-screen display (SRT/ASS)."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned

    words = cleaned.split()
    lines: list[str] = []
    current: list[str] = []
    length = 0

    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > max_chars:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
            if len(lines) >= max_lines:
                break
        else:
            current.append(word)
            length += extra

    if current and len(lines) < max_lines:
        lines.append(" ".join(current))

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if len(lines) == max_lines and len(words) > sum(len(line.split()) for line in lines):
        lines[-1] = lines[-1].rstrip(".,;:") + "…"

    return "\n".join(lines)


def _to_srt_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def chunks_to_srt(chunks: List[Dict]) -> str:
    """
    Convert a list of dictionaries with 'start', 'end', and 'text' keys
    into a valid SubRip (.srt) file content string.
    """
    lines = []
    for i, chunk in enumerate(chunks, 1):
        lines.append(str(i))
        start_ts = _to_srt_timestamp(chunk.get('start', 0))
        end_ts = _to_srt_timestamp(chunk.get('end', 0))
        lines.append(f"{start_ts} --> {end_ts}")
        text = chunk.get("translated_text", chunk.get("text", ""))
        lines.append(wrap_subtitle_text(text.strip()))
        lines.append("")
    return "\n".join(lines)
