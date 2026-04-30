from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
from pydantic import BaseModel, Field
from pathlib import Path
import shutil
import os
import logging
from urllib.parse import urlparse
import requests
import json

# ─── Constants ───────────────────────────────────────────────────────────────
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_TEXT_LENGTH = 50_000  # characters
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
ALLOWED_ASPECT_RATIOS = {"16:9", "9:16", "4:3", "1:1"}
ALLOWED_VIDEO_ENGINES = {"local", "veo3", "kling", "minimax", "seedance"}

from app.core.config import settings
from app.core.jobs import job_manager, JobStatus, JobType
from app.core.logging import mask_api_key
from app.services.pipeline import DubbingPipeline
from app.services.url_service import URLService, URLServiceError
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService
from app.core.worker import worker

logger = logging.getLogger(__name__)
router = APIRouter()
url_service = URLService()
video_service = VideoService()


# ─── Dubbing Endpoints ──────────────────────────────────────────────────────

@router.post("/dub")
async def create_dub_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_lang: str = "vi"
):
    """Upload a video file and start dubbing."""
    file_id = job_manager.create_job(file.filename, job_type=JobType.DUBBING)
    input_path = settings.INPUT_DIR / f"{file_id}_{file.filename}"

    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    worker.add_job(file_id, {
        "source_path": input_path,
        "target_lang": target_lang
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
    target_lang: str = Form("vi")
):
    """Start dubbing from a video URL."""
    job_id = f"url_{os.urandom(4).hex()}"
    job_manager.register_job(job_id, filename=url, job_type=JobType.DUBBING, url=url, target_lang=target_lang)

    worker.add_job(job_id, {
        "source_path": url,
        "target_lang": target_lang
    })

    return {"job_id": job_id}


@router.post("/studio")
async def create_studio_video(
    background_tasks: BackgroundTasks,
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    text: str = Form(...),
    target_lang: str = Form("vi"),
    voice_id: str = Form("vi-VN-HoaiMyNeural"),
    duration_seconds: int = Form(0),
    aspect_ratio: str = Form("16:9"),
):
    """Create a studio video from image + text."""
    if image is None and not image_url:
        raise HTTPException(status_code=400, detail="Please upload an image or provide an image URL.")

    # Input validation
    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Text too long. Maximum {MAX_TEXT_LENGTH} characters.")
    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        raise HTTPException(status_code=400, detail=f"Invalid aspect ratio. Allowed: {', '.join(ALLOWED_ASPECT_RATIOS)}")
    if duration_seconds < 0 or duration_seconds > 600:
        raise HTTPException(status_code=400, detail="duration_seconds must be between 0 and 600.")

    job_id = f"studio_{os.urandom(4).hex()}"
    job_manager.register_job(job_id, filename="studio_project", job_type=JobType.STUDIO, text=text, target_lang=target_lang)

    if image is not None:
        image_filename = image.filename or "studio_image"
        image_path = settings.INPUT_DIR / f"{job_id}_{image_filename}"
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    else:
        image_path = _download_image_to_input(job_id, image_url or "")

    worker.add_job(job_id, {
        "type": JobType.STUDIO,
        "image_path": str(image_path),
        "text": text,
        "target_lang": target_lang,
        "voice_id": voice_id,
        "duration_seconds": max(0, int(duration_seconds)),
        "aspect_ratio": aspect_ratio,
    })

    return {"job_id": job_id}


@router.post("/shorts")
async def create_shorts_video(
    background_tasks: BackgroundTasks,
    prompt: Optional[str] = Form(None),
    script: Optional[str] = Form(None),
    target_lang: str = Form("vi"),
    voice_id: str = Form("vi-VN-HoaiMyNeural"),
    duration_seconds: int = Form(0),
    aspect_ratio: str = Form("9:16"),
    video_engine: str = Form("local"),
):
    """Create a caption-first short video from a prompt or script."""
    cleaned_prompt = (prompt or "").strip()
    cleaned_script = (script or "").strip()
    if not cleaned_prompt and not cleaned_script:
        raise HTTPException(status_code=400, detail="Please provide a prompt or a script.")

    if video_engine not in ALLOWED_VIDEO_ENGINES:
        raise HTTPException(status_code=400, detail=f"Unsupported video engine: {video_engine}")
    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        raise HTTPException(status_code=400, detail=f"Invalid aspect ratio. Allowed: {', '.join(ALLOWED_ASPECT_RATIOS)}")
    if duration_seconds < 0 or duration_seconds > 600:
        raise HTTPException(status_code=400, detail="duration_seconds must be between 0 and 600.")
    if len(cleaned_prompt) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Prompt too long. Maximum {MAX_TEXT_LENGTH} characters.")
    if len(cleaned_script) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Script too long. Maximum {MAX_TEXT_LENGTH} characters.")

    job_id = f"shorts_{os.urandom(4).hex()}"
    job_manager.register_job(
        job_id,
        filename="shorts_project",
        job_type=JobType.SHORTS,
        prompt=cleaned_prompt,
        target_lang=target_lang,
        video_engine=video_engine,
    )

    worker.add_job(job_id, {
        "type": JobType.SHORTS,
        "prompt": cleaned_prompt,
        "script": cleaned_script,
        "target_lang": target_lang,
        "voice_id": voice_id,
        "duration_seconds": max(0, int(duration_seconds)),
        "aspect_ratio": aspect_ratio,
        "video_engine": video_engine,
    })

    return {"job_id": job_id}


def _download_image_to_input(job_id: str, image_url: str) -> Path:
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https image URLs are supported.")

    # Block private/internal IPs (basic SSRF protection)
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
        raise HTTPException(status_code=400, detail="Internal/private URLs are not allowed.")

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
        finally:
            job_manager.unsubscribe(subscriber)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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

    artifacts: dict[str, Optional[str]] = {
        "subtitle_path": None,
        "transcript_path": None,
        "session_dir": None,
    }

    session_dir = settings.TEMP_DIR / job_id
    if session_dir.exists():
        artifacts["session_dir"] = str(session_dir)
        transcript_path = session_dir / "transcript.json"
        subtitle_path = session_dir / "translated.srt"
        if transcript_path.exists():
            artifacts["transcript_path"] = str(transcript_path)
        if subtitle_path.exists():
            artifacts["subtitle_path"] = str(subtitle_path)
    else:
        studio_subtitle = settings.TEMP_DIR / f"{job_id}_tts.vtt"
        if studio_subtitle.exists():
            artifacts["subtitle_path"] = str(studio_subtitle)

    return artifacts


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


# ─── Voice Catalog ──────────────────────────────────────────────────────────

VOICE_CATALOG = [
    # Vietnamese
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My", "lang": "vi", "gender": "Female"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh", "lang": "vi", "gender": "Male"},
    # English
    {"id": "en-US-AriaNeural", "name": "Aria (US)", "lang": "en", "gender": "Female"},
    {"id": "en-US-GuyNeural", "name": "Guy (US)", "lang": "en", "gender": "Male"},
    {"id": "en-US-JennyNeural", "name": "Jenny (US)", "lang": "en", "gender": "Female"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "lang": "en", "gender": "Female"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha (AU)", "lang": "en", "gender": "Female"},
    {"id": "en-CA-LiamNeural", "name": "Liam (CA)", "lang": "en", "gender": "Male"},
    # Japanese
    {"id": "ja-JP-NanamiNeural", "name": "Nanami", "lang": "ja", "gender": "Female"},
    {"id": "ja-JP-KeitaNeural", "name": "Keita", "lang": "ja", "gender": "Male"},
    # Korean
    {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi", "lang": "ko", "gender": "Female"},
    {"id": "ko-KR-InJoonNeural", "name": "InJoon", "lang": "ko", "gender": "Male"},
    # Chinese
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "lang": "zh", "gender": "Female"},
    {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "lang": "zh", "gender": "Male"},
    {"id": "zh-HK-HiuGaaiNeural", "name": "HiuGaai (HK)", "lang": "zh", "gender": "Female"},
    # French
    {"id": "fr-FR-DeniseNeural", "name": "Denise", "lang": "fr", "gender": "Female"},
    {"id": "fr-FR-HenriNeural", "name": "Henri", "lang": "fr", "gender": "Male"},
    # Spanish
    {"id": "es-ES-ElviraNeural", "name": "Elvira", "lang": "es", "gender": "Female"},
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "lang": "es", "gender": "Male"},
    # German
    {"id": "de-DE-KatjaNeural", "name": "Katja", "lang": "de", "gender": "Female"},
    {"id": "de-DE-ConradNeural", "name": "Conrad", "lang": "de", "gender": "Male"},
    # Portuguese
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca (BR)", "lang": "pt", "gender": "Female"},
    {"id": "pt-BR-AntonioNeural", "name": "Antonio (BR)", "lang": "pt", "gender": "Male"},
    # Italian
    {"id": "it-IT-ElsaNeural", "name": "Elsa", "lang": "it", "gender": "Female"},
    {"id": "it-IT-DiegoNeural", "name": "Diego", "lang": "it", "gender": "Male"},
    # Russian
    {"id": "ru-RU-SvetlanaNeural", "name": "Svetlana", "lang": "ru", "gender": "Female"},
    {"id": "ru-RU-DmitryNeural", "name": "Dmitry", "lang": "ru", "gender": "Male"},
    # Thai
    {"id": "th-TH-PremwadeeNeural", "name": "Premwadee", "lang": "th", "gender": "Female"},
    {"id": "th-TH-NiwatNeural", "name": "Niwat", "lang": "th", "gender": "Male"},
    # Hindi
    {"id": "hi-IN-SwaraNeural", "name": "Swara", "lang": "hi", "gender": "Female"},
    {"id": "hi-IN-MadhurNeural", "name": "Madhur", "lang": "hi", "gender": "Male"},
    # Arabic
    {"id": "ar-SA-ZariyahNeural", "name": "Zariyah (SA)", "lang": "ar", "gender": "Female"},
    {"id": "ar-SA-HamedNeural", "name": "Hamed (SA)", "lang": "ar", "gender": "Male"},
    # Indonesian
    {"id": "id-ID-GadisNeural", "name": "Gadis", "lang": "id", "gender": "Female"},
    {"id": "id-ID-ArdiNeural", "name": "Ardi", "lang": "id", "gender": "Male"},
]


@router.get("/voices")
async def list_voices():
    return VOICE_CATALOG


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
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None


@router.post("/settings")
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
