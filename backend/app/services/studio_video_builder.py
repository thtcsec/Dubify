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
from app.utils.studio_script_format import (
    extract_popups_from_text,
    scene_visual_title,
    schedule_popup_timings,
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
    research_topic: str | None = None,
    wiki_thumbnail_url: str = "",
    use_scene_images: bool = True,
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

    topic_label = (research_topic or "").strip()
    # ALWAYS try to fetch scene images — this is what makes videos look professional
    # Extract meaningful topic from script content (not section headers like "Mở đầu")
    if not topic_label:
        # Get actual content keywords from script (skip [Section] headers and [STAT/DEF] markers)
        import re
        clean_script = re.sub(r"\[[^\]]*\]", "", script or "")  # Remove all [brackets]
        clean_script = re.sub(r"\s+", " ", clean_script).strip()
        # Take first meaningful sentence as topic
        sentences = [s.strip() for s in clean_script.split(".") if len(s.strip()) > 10]
        topic_label = sentences[0][:100] if sentences else clean_script[:100]
    fetch_images = bool(topic_label) and bool(use_scene_images)
    if fetch_images:
        from app.services.scene_image_service import resolve_scene_image

    scene_pngs: list[tuple[Path, float]] = []
    # Try animated multi-frame render for smoother motion (Remotion-style)
    use_animated = bool(settings.STUDIO_ANIMATED_RENDER) and settings.STUDIO_RENDER_ENGINE != "pil"
    
    for index, scene in enumerate(timed_scenes):
        png_path = temp_dir / f"scene_{index:03d}.png"
        scene_bg = image_path
        if fetch_images:
            scene_img = temp_dir / f"scene_{index:03d}_bg.jpg"
            scene_bg = resolve_scene_image(
                topic=topic_label,
                scene_title=str(scene.get("title") or ""),
                scene_body=str(scene.get("body") or ""),
                output_path=scene_img,
                fallback_path=image_path,
                scene_index=index,
                wiki_thumbnail_url=wiki_thumbnail_url if index == 0 else "",
            )

        # Render the scene PNG (static capture at animation midpoint)
        ok = renderer.render_scene_png(
            title=scene_visual_title(str(scene.get("title") or "")),
            text=scene_display_text(str(scene.get("body") or ""), max_chars=120),
            image_path=scene_bg,
            output_png=png_path,
        )
        if not ok:
            logger.error("Failed to render studio scene %d", index)
            return False

        duration = max(0.5, scene["end"] - scene["start"])

        # Attempt animated frame sequence for this scene
        if use_animated and duration >= 2.0:
            try:
                from app.services.render_abstraction import SceneRenderer, RenderMode
                animated_renderer = SceneRenderer(
                    mode=RenderMode.ANIMATED,
                    fps=int(getattr(settings, "STUDIO_ANIMATED_FPS", 24)),
                    width=renderer.width,
                    height=renderer.height,
                    scale=float(getattr(settings, "STUDIO_RENDER_SCALE", 1.0)),
                    max_scene_duration=float(getattr(settings, "STUDIO_ANIMATED_MAX_SECONDS", 12.0)),
                )
                html_path = png_path.with_suffix(".html")
                if html_path.exists():
                    frame_dir = temp_dir / f"scene_{index:03d}_frames"
                    frame_dir.mkdir(exist_ok=True)
                    result = animated_renderer.render_scene(
                        html_path, frame_dir, duration, scene_index=index
                    )
                    if result and len(result.frames) >= 3:
                        logger.info(
                            "Animated render: scene %d → %d frames (%.1fs)",
                            index, len(result.frames), duration,
                        )
            except Exception as anim_err:
                logger.debug("Animated render skipped for scene %d: %s", index, anim_err)

        scene_pngs.append((png_path, duration))
        logger.info(
            "Studio scene %d/%d '%s' %.1fs",
            index + 1,
            len(timed_scenes),
            scene["title"] or "untitled",
            duration,
        )

    popups = extract_popups_from_text(script)
    popup_timings = schedule_popup_timings(popups, audio_duration)

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
        popup_timings=popup_timings,
    )
