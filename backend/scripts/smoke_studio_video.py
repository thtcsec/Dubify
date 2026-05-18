#!/usr/bin/env python3
"""Smoke-test Script-to-Video pipeline (TTS + HTML scenes + FFmpeg)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.studio_video_builder import build_html_scene_video
from app.services.tts_service import TTSService
from app.services.video_service import VideoService
from app.utils.studio_background import ensure_studio_background


SCRIPT = (
    "AI không còn chỉ là công nghệ. "
    "Nó đang trở thành vấn đề của cả nhân loại. "
    "Ngày hôm nay Vatican đặt ra một câu hỏi rất thẳng. "
    "Chúng ta cần suy nghĩ lại về đạo đức."
)


async def main() -> int:
    job_id = "smoke_studio"
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    bg = ensure_studio_background(job_id, "9:16", image_path=None)
    tts = TTSService(voice="vi-VN-HoaiMyNeural")
    audio_path, sub_path = await tts.generate_studio_audio_with_subtitles(SCRIPT, "vi", job_id)
    out = settings.TEMP_DIR / f"{job_id}_smoke.mp4"

    ok = build_html_scene_video(
        script=SCRIPT,
        image_path=bg,
        audio_path=audio_path,
        subtitle_path=sub_path,
        output_path=out,
        aspect_ratio="9:16",
        template_name="tiktok_news",
    )
    if not ok or not out.exists():
        print("FAIL: build_html_scene_video returned false or no output")
        return 1

    size = out.stat().st_size
    duration = VideoService.get_duration(out)
    print(f"OK: {out}")
    print(f"  size={size} bytes  duration={duration:.1f}s")

    if size < 20_000:
        print("FAIL: output too small")
        return 1
    if duration < 3.0:
        print("FAIL: duration too short")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
