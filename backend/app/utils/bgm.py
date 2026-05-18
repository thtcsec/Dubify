"""Optional background music mixing for Studio / Shorts outputs."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def mix_bgm_under_voice(
    voice_audio: Path,
    bgm_audio: Path,
    output_path: Path,
    bgm_volume: float = 0.15,
) -> bool:
    """Mix BGM under narration; keep voice duration (first input)."""
    if not voice_audio.exists() or not bgm_audio.exists():
        return False

    volume = max(0.0, min(bgm_volume, 1.0))
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(voice_audio),
        "-i",
        str(bgm_audio),
        "-filter_complex",
        f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map",
        "[aout]",
        "-ac",
        "2",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        if proc.returncode != 0:
            logger.warning("BGM mix failed: %s", stderr.decode(errors="ignore"))
            return False
        return output_path.exists() and output_path.stat().st_size > 0
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        logger.warning("BGM mix timed out")
        return False
