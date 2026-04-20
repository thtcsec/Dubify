from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from pathlib import Path
import shutil
import os
from app.core.config import settings
from app.core.jobs import job_manager, JobStatus
from app.services.pipeline import DubbingPipeline
from app.services.url_service import URLService
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService

router = APIRouter()
url_service = URLService()
video_service = VideoService()

async def run_pipeline_task(job_id: str, video_path: Path, target_lang: str):
    """Background task to run the dubbing pipeline."""
    job_manager.update_job(job_id, JobStatus.PROCESSING)
    
    pipeline = DubbingPipeline(target_lang=target_lang)
    output_path = await pipeline.run(video_path, job_id)
    
    if output_path:
        job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path))
    else:
        job_manager.update_job(job_id, JobStatus.FAILED, error="Pipeline execution failed")

@router.post("/dub")
async def create_dub_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_lang: str = "vi"
):
    # 1. Save uploaded file
    file_id = job_manager.create_job(file.filename)
    input_path = settings.INPUT_DIR / f"{file_id}_{file.filename}"
    
    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. Add to background tasks
    background_tasks.add_task(run_pipeline_task, file_id, input_path, target_lang)
    
    return {
        "job_id": file_id,
        "status": JobStatus.PENDING,
        "message": "Processing started in background"
    }

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/fetch-info")
async def fetch_info(url: str = Form(...)):
    try:
        info = url_service.get_info(url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dub-url")
async def dub_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    target_lang: str = Form("vi")
):
    job_id = f"url_{os.urandom(4).hex()}"
    job_manager.add_job(job_id, {"status": "pending", "url": url, "target_lang": target_lang})
    
    async def process_flow():
        try:
            job_manager.update_job(job_id, {"status": "downloading"})
            local_path = url_service.download_video(url)
            
            pipeline = DubbingPipeline(
                video_service=video_service,
                asr_service=ASRService(),
                translate_service=TranslateService(),
                tts_service=TTSService()
            )
            
            job_manager.update_job(job_id, {"status": "processing"})
            output_path = await pipeline.run(local_path, target_lang)
            job_manager.update_job(job_id, {"status": "completed", "output_path": output_path})
        except Exception as e:
            job_manager.update_job(job_id, {"status": "failed", "error": str(e)})

    background_tasks.add_task(process_flow)
    return {"job_id": job_id}
