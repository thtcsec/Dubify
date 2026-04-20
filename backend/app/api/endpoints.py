from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pathlib import Path
import shutil
from app.core.config import settings
from app.core.jobs import job_manager, JobStatus
from app.services.pipeline import DubbingPipeline

router = APIRouter()

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
