import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

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
        lines.append(chunk.get("text", "").strip())
        lines.append("")
    return "\n".join(lines)
