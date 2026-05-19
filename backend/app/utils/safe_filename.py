"""Safe filesystem basenames for output videos (ASCII-friendly, length-limited)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def safe_basename(title: str, fallback: str = "video", *, max_len: int = 48) -> str:
    """Strip path chars and collapse whitespace; keep Unicode letters/numbers."""
    raw = unicodedata.normalize("NFKC", (title or "").strip())
    raw = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" .")
    if not raw:
        return fallback
    if len(raw) > max_len:
        raw = raw[:max_len].rstrip(" .")
    return raw or fallback


def dubbed_output_filename(job_id: str, source_name: str) -> str:
    stem = Path(source_name).stem if source_name else "video"
    safe = safe_basename(stem, "video")
    return f"{job_id}_dubbed_{safe}.mp4"


def studio_output_filename(job_id: str, title: str) -> str:
    safe = safe_basename(title, "studio")
    return f"{job_id}_{safe}.mp4"
