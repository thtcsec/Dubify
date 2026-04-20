import threading
import queue
import logging
from typing import Dict, Any
from app.services.pipeline import DubbingPipeline
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService
from app.services.url_service import URLService
from app.core.jobs import job_manager, JobStatus

logger = logging.getLogger(__name__)

class BackgroundWorker:
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread.start()
            logger.info("Background worker started.")

    def add_job(self, job_id: str, payload: Dict[str, Any]):
        self.queue.put((job_id, payload))
        logger.info(f"Job {job_id} added to worker queue.")

    def _run(self):
        while self.is_running:
            try:
                # Wait for a job from the queue
                job_id, payload = self.queue.get(timeout=1.0)
                
                try:
                    self._process_job(job_id, payload)
                except Exception as e:
                    logger.error(f"Error processing job {job_id}: {str(e)}")
                    job_manager.update_job(job_id, JobStatus.FAILED, error=str(e))
                finally:
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {str(e)}")

    def _process_job(self, job_id: str, payload: Dict[str, Any]):
        """Execute the actual dubbing pipeline."""
        target_lang = payload.get("target_lang", "vi")
        source_path = payload.get("source_path")
        
        # If it's a URL, download it first
        if isinstance(source_path, str) and (source_path.startswith("http") or "drive.google.com" in source_path):
            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Downloading video from URL...")
            url_service = URLService()
            source_path = url_service.download_video(source_path)

        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Starting AI pipeline...")
        
        # Initialize pipeline with all required services
        pipeline = DubbingPipeline(
            video_service=VideoService(),
            asr_service=ASRService(),
            translate_service=TranslateService(),
            tts_service=TTSService()
        )
        
        # Run pipeline
        # Note: The pipeline.run method signature might vary based on previous implementation
        # Assuming: async def run(self, input_path: Union[str, Path], job_id: str) -> Optional[Path]:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            output_path = loop.run_until_complete(pipeline.run(source_path, job_id))
            if output_path:
                job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path))
            else:
                job_manager.update_job(job_id, JobStatus.FAILED, error="Pipeline returned no output")
        finally:
            loop.close()

# Global worker instance
worker = BackgroundWorker()
