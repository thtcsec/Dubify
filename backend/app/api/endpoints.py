from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form, Query, Depends
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import shutil
import os
import logging
import re
from urllib.parse import urlparse
import requests
import json

# ─── Constants ───────────────────────────────────────────────────────────────
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_TEXT_LENGTH = 50_000  # characters
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
ALLOWED_ASPECT_RATIOS = {"16:9", "9:16", "4:3", "3:4", "1:1"}
ALLOWED_VIDEO_ENGINES = {"series", "local", "single", "veo3", "kling", "minimax", "seedance"}

from app.core.auth import require_admin_key
from app.core.config import settings
from app.core.jobs import job_manager, JobStatus, JobType
from app.core.logging import mask_api_key
from app.core.worker import worker
from app.services.url_service import URLService, URLServiceError
from app.services.tts_service import TTSService
from app.api.voice_catalog import voices_payload
from app.core.gpu import gpu_info_dict
from app.services.editor_service import EditorService
from app.services.video_service import VideoService
from app.utils.artifacts import remove_job_artifacts, resolve_artifact_paths
from app.utils.uploads import save_upload_limited
from app.utils.url_safety import validate_public_http_url

logger = logging.getLogger(__name__)
router = APIRouter()
url_service = URLService()


def _natural_media_sort_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.lower())
    key: list[object] = []
    for part in parts:
        key.append(int(part) if part.isdigit() else part)
    return key


def _aspect_ratio_value(aspect_ratio: str) -> float:
    left, right = (aspect_ratio or "16:9").split(":", 1)
    return max(float(left), 1.0) / max(float(right), 1.0)


def _clip_matches_aspect_ratio(width: int, height: int, aspect_ratio: str, tolerance: float = 0.08) -> bool:
    if width <= 0 or height <= 0:
        return False
    actual = float(width) / float(height)
    expected = _aspect_ratio_value(aspect_ratio)
    return abs(actual - expected) <= tolerance


def _validate_pixverse_clip_paths(paths: list[str], *, aspect_ratio: str) -> None:
    if not paths:
        return
    if len(paths) < 4 or len(paths) > 8:
        raise HTTPException(
            status_code=400,
            detail="Hackathon PixVerse path requires 4-8 clips. Please provide 4-8 MP4 shots.",
        )

    total_duration = 0.0
    for raw_path in paths:
        clip_path = Path(raw_path)
        if not clip_path.exists():
            raise HTTPException(status_code=400, detail=f"PixVerse clip not found: {clip_path.name}")
        try:
            width, height = VideoService.get_video_size(clip_path)
            duration = VideoService.get_duration(clip_path)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not inspect PixVerse clip '{clip_path.name}'. Make sure it is a valid MP4 video.",
            ) from exc

        if duration < 4.0 or duration > 9.0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"PixVerse clip '{clip_path.name}' is {duration:.1f}s. "
                    "For hackathon flow, each shot should stay around 5-8 seconds."
                ),
            )
        if not _clip_matches_aspect_ratio(width, height, aspect_ratio):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"PixVerse clip '{clip_path.name}' has aspect {width}x{height}, "
                    f"which does not match the selected project ratio {aspect_ratio}."
                ),
            )
        total_duration += duration

    if total_duration < 30.0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Total PixVerse clip duration is only {total_duration:.1f}s. "
                "Hackathon submission needs a final video of at least 30 seconds."
            ),
        )


# ─── Dubbing Endpoints ──────────────────────────────────────────────────────

class JobRenameRequest(BaseModel):
    filename: str


@router.post("/dub")
async def create_dub_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_lang: str = "vi",
    voice_id: str = Form(""),
    project_name: str = Form(""),
):
    """Upload a video file and start dubbing."""
    from app.utils.project_title import derive_dub_title

    display_name = derive_dub_title(
        project_name=project_name,
        upload_filename=file.filename or "upload",
    )
    file_id = job_manager.create_job(display_name, job_type=JobType.DUBBING)
    safe_name = Path(file.filename or "upload").name
    input_path = settings.INPUT_DIR / f"{file_id}_{safe_name}"

    await save_upload_limited(file, input_path, MAX_UPLOAD_SIZE)

    default_voice = voice_id.strip() or TTSService.default_voice_for_lang(target_lang)
    worker.add_job(file_id, {
        "source_path": input_path,
        "target_lang": target_lang,
        "voice_id": default_voice,
    })

    return {
        "job_id": file_id,
        "status": JobStatus.PENDING,
        "message": "Processing started in background"
    }


@router.post("/dub-url")
async def dub_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    target_lang: str = Form("vi"),
    voice_id: str = Form(""),
    project_name: str = Form(""),
):
    """Start dubbing from a video URL."""
    from app.utils.project_title import derive_dub_title

    job_id = f"url_{os.urandom(4).hex()}"
    display_name = derive_dub_title(project_name=project_name, url=url)
    default_voice = voice_id.strip() or TTSService.default_voice_for_lang(target_lang)
    job_manager.register_job(job_id, filename=display_name, job_type=JobType.DUBBING, url=url, target_lang=target_lang)

    worker.add_job(job_id, {
        "source_path": url,
        "target_lang": target_lang,
        "voice_id": default_voice,
    })

    return {"job_id": job_id}


@router.post("/studio")
async def create_studio_video(
    background_tasks: BackgroundTasks,
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    pixverse_clips: list[UploadFile] = File([]),
    pixverse_clip_dir: str = Form(""),
    text: str = Form(...),
    target_lang: str = Form("vi"),
    voice_id: str = Form("vi-VN-HoaiMyNeural"),
    duration_seconds: int = Form(0),
    aspect_ratio: str = Form("16:9"),
    use_raw_script: bool = Form(False),
    studio_visual_mode: str = Form("html_scenes"),
    studio_template: str = Form(settings.STUDIO_DEFAULT_TEMPLATE),
    studio_render_engine: str = Form("auto"),
    social_overlay: str = Form("none"),
    social_handle: str = Form(""),
    social_subtitle: str = Form(""),
    social_avatar: Optional[UploadFile] = File(None),
    header_enabled: bool = Form(False),
    header_text: str = Form(""),
    header_opacity: float = Form(0.85),
    header_image: Optional[UploadFile] = File(None),
    footer_enabled: bool = Form(False),
    footer_text: str = Form(""),
    footer_opacity: float = Form(0.85),
    footer_image: Optional[UploadFile] = File(None),
    header_y_pct: float = Form(0.0),
    footer_y_pct: float = Form(89.0),
    social_left_pct: float = Form(4.4),
    social_bottom_pct: float = Form(6.25),
    caption_y_pct: float = Form(64.0),
    research_topic: str = Form(""),
    wiki_thumbnail_url: str = Form(""),
    use_scene_images: bool = Form(settings.STUDIO_USE_SCENE_IMAGES),
    project_name: str = Form(""),
    scene_review_json: str = Form(""),
):
    """Create a studio video from script; background image is optional (gradient if omitted)."""
    # Input validation
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Text too long. Maximum {MAX_TEXT_LENGTH} characters.")
    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        raise HTTPException(status_code=400, detail=f"Invalid aspect ratio. Allowed: {', '.join(ALLOWED_ASPECT_RATIOS)}")
    if duration_seconds < 0 or duration_seconds > 600:
        raise HTTPException(status_code=400, detail="duration_seconds must be between 0 and 600.")

    from app.utils.project_title import derive_studio_title

    job_id = f"studio_{os.urandom(4).hex()}"
    display_name = derive_studio_title(
        project_name=project_name,
        research_topic=research_topic,
        script=text,
    )
    job_manager.register_job(job_id, filename=display_name, job_type=JobType.STUDIO, text=text, target_lang=target_lang)

    image_path: str | None = None
    if image is not None:
        image_filename = image.filename or "studio_image"
        saved = settings.INPUT_DIR / f"{job_id}_{image_filename}"
        with open(saved, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = str(saved)
    elif image_url and image_url.strip():
        image_path = str(_download_image_to_input(job_id, image_url.strip()))

    header_image_path: str | None = None
    footer_image_path: str | None = None
    if header_image is not None and header_image.filename:
        saved = settings.INPUT_DIR / f"{job_id}_header_{Path(header_image.filename).name}"
        with open(saved, "wb") as buffer:
            shutil.copyfileobj(header_image.file, buffer)
        header_image_path = str(saved)
    if footer_image is not None and footer_image.filename:
        saved = settings.INPUT_DIR / f"{job_id}_footer_{Path(footer_image.filename).name}"
        with open(saved, "wb") as buffer:
            shutil.copyfileobj(footer_image.file, buffer)
        footer_image_path = str(saved)

    social_avatar_path: str | None = None
    if social_avatar is not None and social_avatar.filename:
        saved = settings.INPUT_DIR / f"{job_id}_social_{Path(social_avatar.filename).name}"
        with open(saved, "wb") as buffer:
            shutil.copyfileobj(social_avatar.file, buffer)
        social_avatar_path = str(saved)

    pixverse_clip_paths: list[str] = []
    clip_dir = (pixverse_clip_dir or "").strip()
    if clip_dir:
        safe_name = "".join(ch for ch in clip_dir if ch.isalnum() or ch in {"_", "-"}).strip()
        if safe_name != clip_dir:
            raise HTTPException(status_code=400, detail="pixverse_clip_dir contains invalid characters.")
        if safe_name not in {"pixverse_smoke"}:
            raise HTTPException(status_code=400, detail="pixverse_clip_dir is not allowed.")
        import_dir = settings.INPUT_DIR / safe_name
        if not import_dir.exists():
            raise HTTPException(status_code=400, detail=f"pixverse_clip_dir not found: {safe_name}")
        candidates = sorted(import_dir.glob("*.mp4"), key=_natural_media_sort_key)
        if len(candidates) < 1:
            raise HTTPException(status_code=400, detail=f"No .mp4 clips found in pixverse_clip_dir: {safe_name}")
        pixverse_clip_paths.extend([str(p) for p in candidates])

    for index, clip in enumerate(pixverse_clips or []):
        if clip is None or not (clip.filename or "").strip():
            continue
        saved = settings.INPUT_DIR / f"{job_id}_pixverse_{index:02d}_{Path(clip.filename).name}"
        await save_upload_limited(clip, saved, MAX_UPLOAD_SIZE)
        pixverse_clip_paths.append(str(saved))

    _validate_pixverse_clip_paths(pixverse_clip_paths, aspect_ratio=aspect_ratio)

    allowed_templates = {"tiktok_news", "tiktok_news_pill", "news_scene", "pixelle_story"}
    if studio_template not in allowed_templates:
        studio_template = settings.STUDIO_DEFAULT_TEMPLATE

    worker.add_job(job_id, {
        "type": JobType.STUDIO,
        "image_path": image_path,
        "text": text,
        "target_lang": target_lang,
        "voice_id": voice_id,
        "duration_seconds": max(0, int(duration_seconds)),
        "aspect_ratio": aspect_ratio,
        "use_raw_script": use_raw_script,
        "studio_visual_mode": studio_visual_mode,
        "studio_template": studio_template,
        "studio_render_engine": studio_render_engine,
        "social_overlay": social_overlay.strip().lower(),
        "social_handle": social_handle.strip(),
        "social_subtitle": social_subtitle.strip(),
        "social_avatar_path": social_avatar_path,
        "header_enabled": header_enabled,
        "header_text": header_text.strip(),
        "header_opacity": header_opacity,
        "header_image_path": header_image_path,
        "footer_enabled": footer_enabled,
        "footer_text": footer_text.strip(),
        "footer_opacity": footer_opacity,
        "footer_image_path": footer_image_path,
        "header_y_pct": header_y_pct,
        "footer_y_pct": footer_y_pct,
        "social_left_pct": social_left_pct,
        "social_bottom_pct": social_bottom_pct,
        "caption_y_pct": caption_y_pct,
        "research_topic": research_topic.strip(),
        "wiki_thumbnail_url": wiki_thumbnail_url.strip(),
        "use_scene_images": use_scene_images,
        "project_name": display_name,
        "scene_review_json": scene_review_json.strip(),
        "pixverse_clip_paths": pixverse_clip_paths,
    })

    return {"job_id": job_id}


@router.post("/shorts")
async def create_shorts_video(
    background_tasks: BackgroundTasks,
    video_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    target_lang: str = Form("vi"),
    voice_id: str = Form("vi-VN-HoaiMyNeural"),
    max_part_duration: int = Form(60),
    vertical_crop: bool = Form(True),
):
    """Long video (URL or file) → transcribe → dub → auto-cut Part 1, Part 2, … for Shorts/TikTok."""
    cleaned_url = (video_url or "").strip()
    if not cleaned_url and (file is None or not file.filename):
        raise HTTPException(status_code=400, detail="Provide a video URL or upload a file.")

    job_id = f"shorts_{os.urandom(4).hex()}"
    label = cleaned_url or (file.filename if file else "upload")
    job_manager.register_job(
        job_id,
        filename=label,
        job_type=JobType.SHORTS,
        url=cleaned_url or None,
        target_lang=target_lang,
    )

    video_path: str | None = None
    if file is not None and file.filename:
        saved = settings.INPUT_DIR / f"{job_id}_{Path(file.filename).name}"
        await save_upload_limited(file, saved, MAX_UPLOAD_SIZE)
        video_path = str(saved)

    worker.add_job(
        job_id,
        {
            "type": JobType.SHORTS,
            "video_url": cleaned_url,
            "video_path": video_path,
            "target_lang": target_lang,
            "voice_id": voice_id,
            "max_part_duration": max(15, min(int(max_part_duration), 180)),
            "vertical_crop": vertical_crop,
        },
    )

    return {"job_id": job_id}


def _download_image_to_input(job_id: str, image_url: str) -> Path:
    try:
        validate_public_http_url(image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parsed = urlparse(image_url)
    try:
        response = requests.get(image_url, timeout=30, stream=True, headers={"User-Agent": "Dubify/1.0"})
        response.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch image from URL: {exc}") from exc

    content_type = (response.headers.get("content-type") or "").lower()
    if "image" not in content_type:
        response.close()
        raise HTTPException(status_code=400, detail="The provided URL did not return an image.")

    # Check Content-Length header if available
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > MAX_IMAGE_SIZE:
        response.close()
        raise HTTPException(status_code=400, detail=f"Image too large. Maximum {MAX_IMAGE_SIZE // (1024*1024)} MB.")

    suffix = ".jpg"
    if "png" in content_type:
        suffix = ".png"
    elif "webp" in content_type:
        suffix = ".webp"
    elif "gif" in content_type:
        suffix = ".gif"

    image_path = settings.INPUT_DIR / f"{job_id}_remote{suffix}"
    downloaded_size = 0
    try:
        with open(image_path, "wb") as buffer:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > MAX_IMAGE_SIZE:
                        raise HTTPException(status_code=400, detail=f"Image too large. Maximum {MAX_IMAGE_SIZE // (1024*1024)} MB.")
                    buffer.write(chunk)
    finally:
        response.close()

    if not image_path.exists() or image_path.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="Downloaded image is empty.")
    return image_path


# ─── Job Status & History ───────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get current status of a specific job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/events")
async def stream_job_events():
    """Push job updates via Server-Sent Events so clients don't need heavy polling."""
    subscriber = job_manager.subscribe()

    def event_stream():
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    event = subscriber.get(timeout=20)
                    yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                except Exception:
                    yield "event: heartbeat\ndata: {}\n\n"
        except GeneratorExit:
            pass
        finally:
            job_manager.unsubscribe(subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs")
async def get_job_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed, cancelled, paused"),
    job_type: Optional[str] = Query(None, description="Filter by type: dubbing, studio, shorts"),
):
    """Get paginated job history with optional filters."""
    return job_manager.get_history(
        limit=limit,
        offset=offset,
        status_filter=status,
        job_type_filter=job_type,
    )


@router.get("/jobs/{job_id}/artifacts")
async def get_job_artifacts(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resolved = resolve_artifact_paths(job_id)
    return {
        "subtitle_path": str(resolved["subtitle_path"]) if resolved["subtitle_path"] else None,
        "transcript_path": str(resolved["transcript_path"]) if resolved["transcript_path"] else None,
        "audio_path": str(resolved["audio_path"]) if resolved.get("audio_path") else None,
        "source_video_path": str(resolved["source_video_path"]) if resolved.get("source_video_path") else None,
        "session_dir": str(resolved["session_dir"]) if resolved["session_dir"] else None,
    }


@router.get("/jobs/{job_id}/plan-clips")
async def plan_job_clips(
    job_id: str,
    platform: str = "tiktok",
    mode: str = "scene",
    max_duration: float | None = None,
):
    """Preview how a completed dub would be split for Shorts/TikTok."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job must be completed.")

    from app.services.clip_service import ClipService

    try:
        service = ClipService()
        return service.plan_from_job(
            job_id,
            job,
            platform=platform if platform in {"tiktok", "youtube_shorts", "instagram_reels", "custom"} else "tiktok",
            mode=mode if mode in {"scene", "fixed"} else "scene",
            max_duration=max_duration,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ExportClipsRequest(BaseModel):
    clips: list[dict]
    vertical_crop: bool = True


@router.post("/jobs/{job_id}/export-clips")
async def export_job_clips(job_id: str, body: ExportClipsRequest):
    """Export social clips (FFmpeg) from a completed dub output."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job must be completed.")

    from app.services.clip_service import ClipSegment, ClipService

    raw_clips = body.clips or []
    vertical_crop = body.vertical_crop
    if not raw_clips:
        raise HTTPException(status_code=400, detail="No clips provided.")

    segments = [
        ClipSegment(
            start=float(c["start"]),
            end=float(c["end"]),
            label=str(c.get("label") or f"Part {i + 1}"),
        )
        for i, c in enumerate(raw_clips)
    ]

    try:
        service = ClipService()
        exported = service.export_clips(job_id, job, segments, vertical_crop=vertical_crop)
        if not exported:
            raise HTTPException(status_code=500, detail="No clips were exported.")
        return {"job_id": job_id, "clips": exported}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Export clips failed for %s", job_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/jobs/{job_id}/burn-subtitles")
async def burn_job_subtitles(job_id: str, srt: str = Form(...)):
    """Re-merge source video + dubbed audio with edited SRT (Studio Editor export)."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job must be completed before re-rendering.")

    try:
        editor = EditorService()
        output_path = editor.burn_subtitles(job_id, srt)
        job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path))
        return {
            "job_id": job_id,
            "output_path": str(output_path),
            "filename": output_path.name,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Burn subtitles failed for %s", job_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/dubbing/capabilities")
async def dubbing_capabilities():
    """Explain what each processing preset enables (for UI / debugging)."""
    engine = settings.normalized_processing_engine()
    mode = settings.normalized_processing_mode()
    translation = settings.default_translation_service()
    return {
        "processing_engine": engine,
        "processing_mode": mode,
        "translation_service": translation,
        "capabilities": {
            "cloud_llm": settings.allow_cloud_llm(),
            "network_tts": settings.allow_network_tts(),
            "url_import": settings.allow_network_downloads(),
        },
        "gpu": gpu_info_dict(),
        "presets": {
            "hybrid": {
                "translation": "google (online)",
                "tts": "Edge-TTS (online)",
                "asr": "local Whisper",
                "notes": "Best default for dubbing to another language when you have internet.",
            },
            "local_offline": {
                "translation": "NLLB (local)",
                "tts": "Piper / SAPI (offline)",
                "asr": "local Whisper",
                "notes": "Fully offline; translation quality depends on NLLB model; no URL import.",
            },
            "cloud_online": {
                "translation": "google",
                "tts": "Edge-TTS",
                "asr": "local Whisper",
                "notes": "Uses cloud LLM when keys are set; needs network.",
            },
        },
        "tts_voice_by_target_lang": {
            lang: TTSService.default_voice_for_lang(lang)
            for lang in ("vi", "en", "ja", "ko", "zh", "fr", "es", "de")
        },
    }


# ─── Job Control (Cancel / Pause / Resume) ──────────────────────────────────

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending or running job."""
    success = job_manager.cancel_job(job_id)
    if not success:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    logger.info(f"Job {job_id} cancelled by user.")
    return {"status": "cancelled", "job_id": job_id}


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running job."""
    success = job_manager.pause_job(job_id)
    if not success:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=400, detail=f"Cannot pause job with status: {job['status']}")
    logger.info(f"Job {job_id} paused by user.")
    return {"status": "paused", "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused job."""
    success = job_manager.resume_job(job_id)
    if not success:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=400, detail=f"Cannot resume job with status: {job['status']}")
    logger.info(f"Job {job_id} resumed by user.")
    return {"status": "resumed", "job_id": job_id}


@router.patch("/jobs/{job_id}")
async def rename_job(job_id: str, body: JobRenameRequest):
    """Rename a job for display in history/projects."""
    name = (body.filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required.")
    if not job_manager.rename_job(job_id, name):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job_id": job_id, "filename": name[:200]}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a completed/failed/cancelled job from history."""
    from app.utils.job_storage import remove_job_storage

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in (JobStatus.PROCESSING, JobStatus.PENDING, JobStatus.PAUSED):
        raise HTTPException(status_code=400, detail="Cannot delete an active job. Cancel it first.")
    job_manager.delete_job(job_id)
    remove_job_storage(job_id, job)
    logger.info(f"Job {job_id} deleted by user.")
    return {"status": "deleted", "job_id": job_id}


@router.delete("/jobs")
async def delete_all_jobs(
    confirm: str = Query(..., description='Must be exactly "DELETE_ALL"'),
    scope: str = Query("all", description='all = every job; completed = finished outputs only'),
):
    """Purge jobs and related storage (artifacts, temp, clips, inputs, outputs)."""
    from app.utils.job_storage import remove_job_storage

    if confirm != "DELETE_ALL":
        raise HTTPException(status_code=400, detail='Confirmation phrase must be DELETE_ALL')

    scope_norm = (scope or "all").strip().lower()
    if scope_norm not in ("all", "completed"):
        raise HTTPException(status_code=400, detail="scope must be all or completed")

    removed_items = job_manager.purge_jobs(scope=scope_norm)
    for job_id, job in removed_items:
        remove_job_storage(job_id, job)

    logger.info("Purged %s jobs (scope=%s)", len(removed_items), scope_norm)
    return {"status": "purged", "removed": len(removed_items), "scope": scope_norm}


@router.get("/voices")
async def list_voices():
    return voices_payload()


@router.post("/research-video/research")
async def research_video_topic(
    topic: str = Form(...),
    target_lang: str = Form("vi"),
):
    """Beta: research a topic and return script + sources for Studio render."""
    from app.services.research_video_service import ResearchVideoService

    if len(topic) > 500:
        raise HTTPException(status_code=400, detail="Topic must be under 500 characters.")
    try:
        return ResearchVideoService.research_topic(topic, target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/research-video/research-stream")
async def research_video_topic_stream(
    topic: str = Form(...),
    target_lang: str = Form("vi"),
):
    """NDJSON stream of research phases (Wikipedia → draft → verify → done)."""
    from app.services.research_video_service import ResearchVideoService

    if len(topic) > 500:
        raise HTTPException(status_code=400, detail="Topic must be under 500 characters.")

    def event_stream():
        try:
            for event in ResearchVideoService.research_topic_iter(topic, target_lang):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except ValueError as exc:
            yield json.dumps({"phase": "error", "message": str(exc)}) + "\n"
        except Exception as exc:
            logger.exception("Research stream failed")
            yield json.dumps({"phase": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/studio/rewrite-script")
async def rewrite_studio_script(
    text: str = Form(...),
    target_lang: str = Form("vi"),
):
    """Rewrite notes into scene-based script with [STAT]/[DEF] popup markers."""
    from app.services.script_service import ScriptService

    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Text too long. Maximum {MAX_TEXT_LENGTH} characters.")
    try:
        script = ScriptService.rewrite_studio_script(text, target_lang)
        return {"script": script}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/voice-preview")
async def preview_voice(voice_id: str = Form(...), text: str = Form("Xin chào, đây là bản xem trước giọng nói.")):
    """Generate voice preview using the active TTS backend."""
    suffix = ".wav" if not settings.allow_network_tts() else ".mp3"
    tmp_path = settings.TEMP_DIR / f"preview_{voice_id.replace('-', '_')}{suffix}"
    try:
        tts_service = TTSService(voice=voice_id)
        success = await tts_service.generate_audio(text, tmp_path)
        if not success:
            raise HTTPException(status_code=400, detail="Voice preview failed: no audio generated.")

        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail=f"No audio generated for voice '{voice_id}'.")

        media_type = "audio/wav" if suffix == ".wav" else "audio/mpeg"
        filename = "preview.wav" if suffix == ".wav" else "preview.mp3"
        return FileResponse(path=str(tmp_path), media_type=media_type, filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice preview failed for voice_id={voice_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Voice preview failed: {str(e)}")


@router.post("/fetch-info")
async def fetch_info(url: str = Form(...)):
    try:
        info = url_service.get_info(url)
        return info
    except URLServiceError as e:
        detail = {
            "message": str(e),
            "hints": e.hints,
        }
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Settings (API keys masked for security) ────────────────────────────────

@router.get("/settings")
async def get_settings():
    """Return settings with API keys masked. Never expose raw keys."""
    return {
        "project_name": settings.PROJECT_NAME,
        "base_dir": str(settings.BASE_DIR),
        "storage_dir": str(settings.STORAGE_DIR),
        "models_dir": str(settings.MODELS_DIR),
        "processing_engine": settings.normalized_processing_engine(),
        "processing_mode": settings.normalized_processing_mode(),
        "capabilities": {
            "cloud_llm": settings.allow_cloud_llm(),
            "network_tts": settings.allow_network_tts(),
            "url_import": settings.allow_network_downloads(),
        },
        "cloud_status": {
            "ready": settings.cloud_engine_ready(),
            "configured_providers": settings.configured_cloud_providers(),
            "message": settings.cloud_engine_message(),
        },
        "local_tts_status": {
            "ready": settings.piper_ready(),
            "engine": "piper",
            "available_models": settings.piper_available_models(),
            "message": settings.local_tts_message(),
        },
        "whisper_model": settings.DEFAULT_WHISPER_MODEL,
        "nllb_model": settings.DEFAULT_NLLB_MODEL,
        "llm_model": (settings.LLM_MODEL or "auto").strip(),
        "llm_models": __import__("app.services.llm_models", fromlist=["LLM_MODEL_CATALOG"]).LLM_MODEL_CATALOG,
        "openai_api_key": mask_api_key(settings.OPENAI_API_KEY),
        "anthropic_api_key": mask_api_key(settings.ANTHROPIC_API_KEY),
        "gemini_api_key": mask_api_key(settings.GEMINI_API_KEY),
        "groq_api_key": mask_api_key(settings.GROQ_API_KEY),
        # Indicate which keys are configured (without exposing values)
        "keys_configured": {
            "openai": bool(settings.OPENAI_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "groq": bool(settings.GROQ_API_KEY),
        }
    }


class SettingsUpdate(BaseModel):
    processing_engine: Optional[str] = None
    processing_mode: Optional[str] = None
    llm_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None


@router.post("/settings", dependencies=[Depends(require_admin_key)])
async def update_settings(data: SettingsUpdate):
    """Update API keys. Values are persisted to .env file."""
    try:
        from dotenv import set_key
        env_path = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")

        if not os.path.exists(env_path):
            Path(env_path).touch()

        if data.processing_engine is not None:
            normalized_engine = (data.processing_engine or "local").strip().lower()
            if normalized_engine not in {"local", "cloud"}:
                raise HTTPException(status_code=400, detail="processing_engine must be 'local' or 'cloud'")
            set_key(env_path, "PROCESSING_ENGINE", normalized_engine)
            settings.PROCESSING_ENGINE = normalized_engine

        if data.processing_mode is not None:
            normalized_mode = (data.processing_mode or "hybrid").strip().lower()
            if normalized_mode not in {"offline", "hybrid", "online"}:
                raise HTTPException(status_code=400, detail="processing_mode must be 'offline', 'hybrid', or 'online'")
            set_key(env_path, "PROCESSING_MODE", normalized_mode)
            settings.PROCESSING_MODE = normalized_mode

        if data.llm_model is not None:
            model_id = (data.llm_model or "auto").strip()
            set_key(env_path, "LLM_MODEL", model_id)
            settings.LLM_MODEL = model_id

        if data.openai_api_key is not None:
            set_key(env_path, "OPENAI_API_KEY", data.openai_api_key)
            settings.OPENAI_API_KEY = data.openai_api_key

        if data.anthropic_api_key is not None:
            set_key(env_path, "ANTHROPIC_API_KEY", data.anthropic_api_key)
            settings.ANTHROPIC_API_KEY = data.anthropic_api_key

        if data.gemini_api_key is not None:
            set_key(env_path, "GEMINI_API_KEY", data.gemini_api_key)
            settings.GEMINI_API_KEY = data.gemini_api_key

        if data.groq_api_key is not None:
            set_key(env_path, "GROQ_API_KEY", data.groq_api_key)
            settings.GROQ_API_KEY = data.groq_api_key

        logger.info("Settings updated by user.")
        warning = None
        if settings.normalized_processing_engine() == "cloud" and not settings.cloud_engine_ready():
            warning = "Cloud engine selected, but no supported API key is configured yet."
        return {"status": "success", "message": "Settings updated", "warning": warning}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
