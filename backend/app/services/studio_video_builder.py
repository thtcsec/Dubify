"""Build studio videos from HTML scene cards (Pixelle-Video-inspired pipeline)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
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


def _resolved_topic_label(script: str, research_topic: str | None) -> str:
    topic_label = (research_topic or "").strip()
    if topic_label:
        return topic_label

    import re

    clean_script = re.sub(r"\[[^\]]*\]", "", script or "")
    clean_script = re.sub(r"\s+", " ", clean_script).strip()
    sentences = [s.strip() for s in clean_script.split(".") if len(s.strip()) > 10]
    return sentences[0][:100] if sentences else clean_script[:100]


def _parse_scene_review_json(
    scene_review_json: str,
    timed_scenes: list[dict],
) -> list["StoryboardScene"]:
    from services.pixverse_adapter import StoryboardScene

    if scene_review_json.strip():
        try:
            payload = json.loads(scene_review_json)
        except json.JSONDecodeError:
            logger.warning("Invalid scene review JSON, falling back to parsed storyboard.")
            payload = []
        if isinstance(payload, list):
            reviewed: list[StoryboardScene] = []
            for index, item in enumerate(payload):
                if not isinstance(item, dict):
                    continue
                description = str(
                    item.get("description") or item.get("text") or item.get("body") or ""
                ).strip()
                title = str(item.get("title") or f"Scene {index + 1}").strip()
                duration = int(item.get("duration_seconds") or item.get("durationSeconds") or 6)
                reviewed.append(
                    StoryboardScene(
                        scene_id=str(item.get("scene_id") or item.get("sceneId") or f"scene_{index + 1:02d}"),
                        title=title,
                        description=description or title,
                        duration_seconds=duration,
                        approved=bool(item.get("approved", True)),
                        prompt_override=str(item.get("prompt") or "").strip(),
                        force_fallback=bool(item.get("force_fallback") or item.get("forceFallback")),
                    )
                )
            if reviewed:
                return reviewed

    fallback_scenes: list[StoryboardScene] = []
    for index, scene in enumerate(timed_scenes):
        fallback_scenes.append(
            StoryboardScene(
                scene_id=f"scene_{index + 1:02d}",
                title=str(scene.get("title") or f"Scene {index + 1}"),
                description=str(scene.get("body") or scene.get("title") or "").strip(),
                duration_seconds=max(5, round(float(scene.get("end", 0.0)) - float(scene.get("start", 0.0))) or 6),
                approved=True,
            )
        )
    return fallback_scenes


def _resolve_storyboard_match(scene_id: str, storyboard_scenes: list["StoryboardScene"]) -> "StoryboardScene | None":
    for scene in storyboard_scenes:
        if scene.scene_id == scene_id:
            return scene
    for scene in storyboard_scenes:
        if scene_id.startswith(scene.scene_id):
            return scene
    return storyboard_scenes[0] if storyboard_scenes else None


def _render_local_pixverse_clip(
    *,
    output_path: Path,
    fallback_image: Path,
    duration: float,
    aspect_ratio: str,
    scene_index: int,
) -> bool:
    width, height = VideoService._canvas_size(aspect_ratio)
    motion_filter = VideoService._scene_motion_filter(width, height, duration, scene_index)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(fallback_image),
        "-t",
        f"{max(duration, 5.0):.3f}",
        "-vf",
        motion_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(settings.STUDIO_SEGMENT_CRF),
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return output_path.exists() and output_path.stat().st_size > 0
    except subprocess.CalledProcessError as exc:
        logger.error("PixVerse fallback clip failed: %s", exc.stderr.decode(errors="replace")[:500])
        return False


def _mux_video_with_audio_and_subtitles(
    *,
    video_only: Path,
    audio_path: Path,
    output_path: Path,
    subtitle_path: Path,
    aspect_ratio: str,
    caption_y_pct: float | None,
    popup_timings: list[tuple[float, float, dict[str, str]]] | None,
    metadata: dict[str, str] | None = None,
    progress_callback: Optional[Callable[[float], None]],
) -> bool:
    vf_parts: list[str] = []
    audio_duration = max(VideoService.get_duration(audio_path), 1.0)
    if subtitle_path.exists():
        cues = (
            VideoService._parse_vtt(subtitle_path)
            if subtitle_path.suffix.lower() == ".vtt"
            else VideoService._parse_srt(subtitle_path)
        )
        if cues:
            width, height = VideoService._canvas_size(aspect_ratio)
            ass_path = output_path.with_suffix(".ass")
            VideoService._create_burn_ass(cues, ass_path, (width, height), font_scale=1.35)
            if popup_timings:
                VideoService._append_popup_overlay_dialogues(
                    ass_path,
                    popup_timings,
                    (width, height),
                    caption_y_pct=caption_y_pct,
                )
            vf_parts.append(f"ass='{VideoService._ffmpeg_subtitle_path(ass_path)}'")

    grain_vignette = VideoService._grain_vignette_filter().lstrip(",")
    if grain_vignette:
        vf_parts.append(grain_vignette)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_only),
        "-i",
        str(audio_path),
    ]
    if metadata:
        for key, value in metadata.items():
            if not key or value is None:
                continue
            command.extend(["-metadata", f"{key}={str(value)}"])
    if vf_parts:
        command.extend(["-vf", ",".join(vf_parts), "-c:v", "libx264", "-preset", "fast", "-crf", str(settings.STUDIO_OUTPUT_CRF)])
    else:
        command.extend(["-c:v", "copy"])
    command.extend(
        [
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            f"{audio_duration:.3f}",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return VideoService._run_ffmpeg_with_progress(
        command,
        duration=audio_duration,
        progress_callback=progress_callback,
    )


def _build_pixverse_scene_video(
    *,
    script: str,
    image_path: Path,
    audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    aspect_ratio: str,
    progress_callback: Optional[Callable[[float], None]],
    research_topic: str | None,
    wiki_thumbnail_url: str,
    use_scene_images: bool,
    timed_scenes: list[dict],
    layout_cfg,
    popup_timings: list[tuple[float, float, dict[str, str]]] | None,
    scene_review_json: str,
    status_callback: Optional[Callable[[str, bool], None]],
    pixverse_clip_paths: list[str] | None = None,
) -> bool:
    from app.services.scene_image_service import resolve_scene_image
    from services.pixverse_adapter import PixVerseAdapter

    storyboard_scenes = _parse_scene_review_json(scene_review_json, timed_scenes)
    adapter = PixVerseAdapter(
        api_key=settings.PIXVERSE_API_KEY,
        api_base=settings.PIXVERSE_API_BASE,
        timeout_seconds=settings.PIXVERSE_TIMEOUT_SECONDS,
    )
    plan = adapter.build_plan(storyboard_scenes, aspect_ratio=aspect_ratio)
    if progress_callback:
        progress_callback(0.1)

    clip_paths: list[Path] = []
    for clip in pixverse_clip_paths or []:
        if clip:
            clip_paths.append(Path(clip))
    has_api = bool(settings.PIXVERSE_API_KEY)

    if has_api and not clip_paths:
        try:
            balance = adapter.get_credit_balance()
            credits_total = int(balance.get("credit_monthly") or 0) + int(balance.get("credit_package") or 0)
            logger.info(
                "[PIXVERSE] Credit balance: monthly=%s package=%s (account_id=%s)",
                balance.get("credit_monthly"),
                balance.get("credit_package"),
                balance.get("account_id"),
            )
            if credits_total <= 0:
                raise RuntimeError(
                    "PixVerse Platform API balance is 0 (Platform API credits are separate from PixVerse Web membership). "
                    "Upload PixVerse MP4 clips per scene in Step 3, or subscribe/top up API credits at https://platform.pixverse.ai/billing."
                )
        except Exception as e:
            raise

    provider_key = "pixverse_external" if clip_paths else ("pixverse" if has_api else "local_fallback")
    if status_callback:
        status_callback(provider_key, not (bool(clip_paths) or has_api))

    temp_dir = settings.TEMP_DIR / f"pixverse_{output_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    topic_label = _resolved_topic_label(script, research_topic)
    segment_paths: list[Path] = []
    shot_provenance: list[dict] = []

    for index, shot in enumerate(plan.shots):
        source_scene = _resolve_storyboard_match(shot.scene_id, storyboard_scenes)
        fallback_image = image_path
        if use_scene_images and topic_label:
            scene_image = temp_dir / f"shot_{index:03d}_bg.jpg"
            fallback_image = resolve_scene_image(
                topic=topic_label,
                scene_title=(source_scene.title if source_scene else "") or f"Shot {index + 1}",
                scene_body=(source_scene.description if source_scene else shot.prompt) or shot.prompt,
                output_path=scene_image,
                fallback_path=image_path,
                scene_index=index,
                wiki_thumbnail_url=wiki_thumbnail_url if index == 0 else "",
            )

        if index < len(clip_paths) and clip_paths[index].exists():
            segment_paths.append(clip_paths[index])
            shot_provenance.append(
                {
                    "shot_id": shot.shot_id,
                    "scene_id": shot.scene_id,
                    "duration_seconds": int(shot.duration_seconds),
                    "source": "pixverse_external",
                    "path": str(clip_paths[index]),
                    "bytes": int(clip_paths[index].stat().st_size),
                }
            )
        else:
            force_fallback = bool(source_scene.force_fallback) if source_scene else False
            if has_api and not force_fallback:
                generated = temp_dir / f"pixverse_{shot.shot_id}.mp4"
                try:
                    logger.info(
                        "[PIXVERSE] Generating %s (%ss, %s)",
                        shot.shot_id,
                        int(shot.duration_seconds),
                        plan.aspect_ratio,
                    )
                    generated_path, prov = adapter.generate_text_to_video_with_provenance(
                        prompt=shot.prompt,
                        aspect_ratio=plan.aspect_ratio,
                        duration_seconds=int(shot.duration_seconds),
                        output_path=generated,
                        model="v6",
                        quality="720p",
                        seed=0,
                        water_mark=False,
                    )
                    logger.info("[PIXVERSE] Saved %s", str(generated_path))
                    segment_paths.append(generated_path)
                    shot_provenance.append(
                        {
                            "shot_id": shot.shot_id,
                            "scene_id": shot.scene_id,
                            "duration_seconds": int(shot.duration_seconds),
                            "source": "pixverse_api",
                            "path": str(generated_path),
                            "pixverse": {
                                "video_id": prov.get("video_id"),
                                "trace_id": prov.get("trace_id"),
                                "api_base": prov.get("api_base"),
                                "result_url": prov.get("result_url"),
                            },
                        }
                    )
                except Exception:
                    logger.exception("[PIXVERSE] Shot %s generation failed; using fallback clip.", shot.shot_id)
                    force_fallback = True

            if force_fallback or not has_api:
                fallback_path = Path(adapter.local_fallback_asset(index, aspect_ratio))
                if not fallback_path.is_absolute():
                    fallback_path = settings.BASE_DIR / fallback_path
                if not _render_local_pixverse_clip(
                    output_path=fallback_path,
                    fallback_image=fallback_image,
                    duration=float(shot.duration_seconds),
                    aspect_ratio=aspect_ratio,
                    scene_index=index,
                ):
                    return False
                segment_paths.append(fallback_path)
                shot_provenance.append(
                    {
                        "shot_id": shot.shot_id,
                        "scene_id": shot.scene_id,
                        "duration_seconds": int(shot.duration_seconds),
                        "source": "local_fallback",
                        "path": str(fallback_path),
                        "fallback_image": str(fallback_image),
                    }
                )
        if progress_callback:
            progress_callback(min(0.2 + ((index + 1) / max(len(plan.shots), 1)) * 0.45, 0.7))

    if not segment_paths:
        return False
    if status_callback:
        status_callback(
            provider_key,
            any(str(item.get("source")) == "local_fallback" for item in shot_provenance),
        )

    video_only = temp_dir / "pixverse_merged.mp4"
    total_segment_duration = sum(max(VideoService.get_duration(path), 0.0) for path in segment_paths)
    transition_count = max(len(segment_paths) - 1, 0)
    fade_seconds = 0.35
    # Keep final length at or above the hackathon minimum instead of shaving time off with transitions.
    if transition_count > 0 and (total_segment_duration - (fade_seconds * transition_count)) < 30.0:
        fade_seconds = 0.0
    if len(segment_paths) == 1:
        shutil.copy2(segment_paths[0], video_only)
    else:
        VideoService._xfade_chain(segment_paths, video_only, fade_seconds=fade_seconds)

    api_shots = [item for item in shot_provenance if str(item.get("source")) == "pixverse_api"]
    trace_hint = ""
    if api_shots:
        trace_hint = str((api_shots[0].get("pixverse") or {}).get("trace_id") or "")
    provenance_out = output_path.with_suffix(".pixverse_provenance.json")
    provenance_out.write_text(
        json.dumps(
            {
                "provider": provider_key,
                "aspect_ratio": aspect_ratio,
                "output_path": str(output_path),
                "video_only_path": str(video_only),
                "audio_path": str(audio_path),
                "subtitle_path": str(subtitle_path),
                "transition_seconds": fade_seconds,
                "shots": shot_provenance,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if _mux_video_with_audio_and_subtitles(
        video_only=video_only,
        audio_path=audio_path,
        output_path=output_path,
        subtitle_path=subtitle_path,
        aspect_ratio=aspect_ratio,
        caption_y_pct=layout_cfg.caption_y_pct,
        popup_timings=popup_timings,
        metadata={
            "comment": f"dubify_provider={provider_key};pixverse_api_shots={len(api_shots)};trace={trace_hint}".strip(";"),
        },
        progress_callback=progress_callback,
    ):
        return True

    return False


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
    scene_review_json: str = "",
    status_callback: Optional[Callable[[str, bool], None]] = None,
    pixverse_clip_paths: list[str] | None = None,
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

    topic_label = _resolved_topic_label(script, research_topic)
    fetch_images = bool(topic_label) and bool(use_scene_images)
    if fetch_images:
        from app.services.scene_image_service import resolve_scene_image

    popups = extract_popups_from_text(script)
    popup_timings = schedule_popup_timings(popups, audio_duration)

    enable_pixverse = bool(settings.ENABLE_PIXVERSE_PRODUCER) and (bool(pixverse_clip_paths) or bool(settings.PIXVERSE_API_KEY))
    if enable_pixverse:
        try:
            pixverse_ok = _build_pixverse_scene_video(
                script=script,
                image_path=image_path,
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                progress_callback=progress_callback,
                research_topic=research_topic,
                wiki_thumbnail_url=wiki_thumbnail_url,
                use_scene_images=use_scene_images,
                timed_scenes=timed_scenes,
                layout_cfg=layout_cfg,
                popup_timings=popup_timings,
                scene_review_json=scene_review_json,
                status_callback=status_callback,
                pixverse_clip_paths=pixverse_clip_paths,
            )
        except Exception as pixverse_err:
            logger.exception(f"[PIXVERSE] Critical error in PixVerse pipeline: {pixverse_err}")
            raise
        if pixverse_ok:
            return True
        raise RuntimeError("PixVerse producer path failed.")
    else:
        logger.info("Using standard HTML/Stock render path.")

    scene_pngs: list[tuple[Path, float]] = []
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
        if use_animated and duration >= 2.0:
            try:
                from app.services.render_abstraction import RenderMode, SceneRenderer

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
                            index,
                            len(result.frames),
                            duration,
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

    success = VideoService.studio_scenes_to_video(
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
    return success
