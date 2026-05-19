"""Build studio videos from HTML scene cards (Pixelle-Video-inspired pipeline)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from app.core.config import settings
from app.services.studio_html_service import StudioHtmlService
from app.services.video_service import VideoService
from app.utils.studio_scenes import (
    assign_scene_timings,
    assign_scene_timings_proportional,
    parse_studio_scenes,
    scene_display_text,
)


def _scene_timings_from_subtitles(
    scenes,
    subtitle_path: Path,
    audio_duration: float,
) -> list[dict]:
    if not subtitle_path.exists():
        return assign_scene_timings_proportional(scenes, audio_duration, min_scene=3.0)

    suffix = subtitle_path.suffix.lower()
    if suffix == ".vtt":
        cues = VideoService._parse_vtt(subtitle_path)
    elif suffix == ".srt":
        cues = VideoService._parse_srt(subtitle_path)
    else:
        cues = []

    if len(cues) < 2:
        return assign_scene_timings_proportional(scenes, audio_duration, min_scene=3.0)

    starts = [float(start) for start, _end, _text in cues]
    ends = [float(end) for _start, end, _text in cues]
    return assign_scene_timings(scenes, starts, ends, audio_duration)

logger = logging.getLogger(__name__)


def build_html_scene_video(
    *,
    script: str,
    image_path: Path,
    audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    aspect_ratio: str,
    template_name: str = "tiktok_news",
    social_overlay: Optional[dict] = None,
    studio_layout: Optional[dict] = None,
    render_engine: str | None = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    scenes = parse_studio_scenes(script)
    if not scenes:
        logger.warning("No studio scenes parsed; falling back to classic render.")
        return False

    audio_duration = max(VideoService.get_duration(audio_path), 1.0)
    timed_scenes = _scene_timings_from_subtitles(scenes, subtitle_path, audio_duration)
    logger.info("Studio: %d scenes over %.1fs audio", len(timed_scenes), audio_duration)
    from app.utils.studio_overlay import SocialOverlayConfig, parse_social_overlay, parse_studio_layout

    overlay_cfg = (
        parse_social_overlay(social_overlay)
        if isinstance(social_overlay, dict)
        else SocialOverlayConfig()
    )
    layout_cfg = (
        parse_studio_layout(studio_layout, aspect_ratio=aspect_ratio)
        if isinstance(studio_layout, dict)
        else parse_studio_layout({}, aspect_ratio=aspect_ratio)
    )
    renderer = StudioHtmlService(
        aspect_ratio=aspect_ratio,
        template_name=template_name,
        social_overlay=overlay_cfg,
        render_engine=render_engine,
        studio_layout=layout_cfg,
    )
    temp_dir = settings.TEMP_DIR / f"studio_html_{output_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    scene_pngs: list[tuple[Path, float]] = []
    for index, scene in enumerate(timed_scenes):
        png_path = temp_dir / f"scene_{index:03d}.png"
        # Visual = background + optional scene title only; speech text via karaoke ASS burn.
        ok = renderer.render_scene_png(
            title=scene["title"],
            text="",
            image_path=image_path,
            output_png=png_path,
        )
        if not ok:
            logger.error("Failed to render studio scene %d", index)
            return False
        duration = max(0.5, scene["end"] - scene["start"])
        scene_pngs.append((png_path, duration))
        logger.info(
            "Studio scene %d/%d '%s' %.1fs",
            index + 1,
            len(timed_scenes),
            scene["title"] or "untitled",
            duration,
        )

    return VideoService.studio_scenes_to_video(
        scene_pngs,
        audio_path,
        output_path,
        srt_path=subtitle_path,
        aspect_ratio=aspect_ratio,
        progress_callback=progress_callback,
        fade_seconds=0.65,
        burn_subtitles=True,
        karaoke_subs=True,
        caption_y_pct=layout_cfg.caption_y_pct,
    )
