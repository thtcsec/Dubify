"""
Background Worker with cancel/pause awareness.

The worker checks job_manager.is_cancelled() and job_manager.wait_if_paused()
between pipeline steps so jobs can be interrupted gracefully.
"""

import threading
import queue
import logging
import asyncio
from typing import Dict, Any
from app.services.pipeline import DubbingPipeline
from app.services.dubbing_reporter import CallbackDubbingReporter
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService
from app.services.url_service import URLService
from app.services.llm_service import LLMService
from app.services.script_service import ScriptService
from app.utils.bgm import mix_bgm_under_voice
from app.services.video_gen_service import VideoGenService
from app.core.config import settings
from app.core.jobs import job_manager, JobStatus, JobType
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    """Raised when a job is cancelled mid-execution."""
    pass


class BackgroundWorker:
    def __init__(self):
        self.queue: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.is_running = False

    def start(self):
        if not self.is_running:
            if not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run, daemon=True)
            self.is_running = True
            self.thread.start()
            logger.info("Background worker started.")

    def stop(self, timeout: int = 10):
        """Graceful shutdown — waits for current job to finish."""
        self.is_running = False
        if self.thread.is_alive():
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                logger.warning("Worker thread did not stop within %ss timeout.", timeout)
        logger.info("Background worker stopped.")

    def add_job(self, job_id: str, payload: Dict[str, Any]):
        self.queue.put((job_id, payload))
        logger.info(f"Job {job_id} added to worker queue.")

    def _check_cancelled(self, job_id: str):
        """Raise CancelledError if job was cancelled."""
        if job_manager.is_cancelled(job_id):
            raise CancelledError(f"Job {job_id} was cancelled by user.")

    async def _maybe_mix_bgm(self, job_id: str, audio_path: Path, _loop=None) -> Path:
        bgm_path = ScriptService.resolve_bgm_path()
        if not bgm_path:
            return audio_path
        mixed = settings.TEMP_DIR / f"{job_id}_with_bgm.wav"
        ok = await mix_bgm_under_voice(
            Path(audio_path),
            bgm_path,
            mixed,
            bgm_volume=settings.STUDIO_BGM_VOLUME,
        )
        if ok:
            logger.info("Mixed BGM %s into job %s", bgm_path.name, job_id)
            return mixed
        return audio_path

    def _check_pause_and_cancel(self, job_id: str):
        """Wait if paused, raise if cancelled."""
        cancelled = job_manager.wait_if_paused(job_id)
        if cancelled:
            raise CancelledError(f"Job {job_id} was cancelled while paused.")
        self._check_cancelled(job_id)

    def _run(self):
        while self.is_running:
            try:
                job_id, payload = self.queue.get(timeout=1.0)

                # Skip if already cancelled while in queue
                if job_manager.is_cancelled(job_id):
                    logger.info(f"Job {job_id} was cancelled before processing. Skipping.")
                    self.queue.task_done()
                    continue

                try:
                    self._process_job(job_id, payload)
                except CancelledError:
                    logger.info(f"Job {job_id} cancelled during processing.")
                    job_manager.update_job(job_id, JobStatus.CANCELLED, message="Cancelled by user")
                except Exception as e:
                    logger.error(f"Error processing job {job_id}: {e}")
                    job_manager.update_job(job_id, JobStatus.FAILED, error=str(e))
                finally:
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")

    def _process_job(self, job_id: str, payload: Dict[str, Any]):
        """Execute the target pipeline."""
        job_type = payload.get("type", JobType.DUBBING)

        if job_type == JobType.STUDIO:
            self._process_studio_job(job_id, payload)
        elif job_type == JobType.SHORTS:
            self._process_shorts_job(job_id, payload)
        else:
            self._process_dubbing_job(job_id, payload)

    def _process_studio_job(self, job_id: str, payload: Dict[str, Any]):
        logger.info(f"Starting Studio processing for job {job_id}")
        target_lang = payload.get("target_lang", "vi")
        raw_text = payload.get("text", "")
        image_path = payload.get("image_path")
        voice_id = payload.get("voice_id", "vi-VN-HoaiMyNeural")
        duration_seconds = int(payload.get("duration_seconds") or 0)
        aspect_ratio = payload.get("aspect_ratio", "16:9")
        use_raw_script = bool(payload.get("use_raw_script", True))

        if not image_path or not os.path.exists(image_path):
            raise ValueError("Background image not found for Studio Job.")

        self._check_pause_and_cancel(job_id)
        step1_msg = "Step 1/3: Preparing script..." if use_raw_script else "Step 1/3: Rewriting script with LLM..."
        job_manager.update_job(job_id, JobStatus.PROCESSING, message=step1_msg, progress=5)
        script = ScriptService.resolve_studio_script(raw_text, target_lang, use_raw_script=use_raw_script)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 1/3: Script ready.", progress=30)

        # Step 2/3: TTS (30% -> 70%)
        self._check_pause_and_cancel(job_id)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 2/3: Generating voiceover (TTS)...", progress=35)
        import asyncio
        import os
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()

        try:
            tts_service = TTSService(voice=voice_id, target_lang=target_lang)
            audio_path, srt_path = loop.run_until_complete(
                tts_service.generate_audio_with_subtitles(script, target_lang, job_id)
            )
            audio_path = loop.run_until_complete(self._maybe_mix_bgm(job_id, audio_path))

            if duration_seconds > 0:
                stretched_audio = settings.TEMP_DIR / f"{job_id}_tts_stretched.wav"
                if VideoService.stretch_audio(audio_path, stretched_audio, duration_seconds):
                    audio_path = stretched_audio
                else:
                    logger.warning("Could not stretch audio to %ss for job %s", duration_seconds, job_id)

            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 2/3: Voiceover generated.", progress=70)

            # Step 3/3: Video Assembly (70% -> 100%)
            self._check_pause_and_cancel(job_id)
            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 3/3: Assembling final video...", progress=75)
            output_filename = f"{job_id}_studio.mp4"
            output_path = settings.OUTPUT_DIR / output_filename
            def update_render_progress(ratio: float):
                progress = 75 + (ratio * 23)
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=f"Step 3/3: Rendering final video... {int(ratio * 100)}%",
                    progress=round(progress, 1),
                )

            success = VideoService.image_audio_to_video(
                image_path=Path(image_path),
                audio_path=audio_path,
                output_path=output_path,
                srt_path=srt_path,
                font_size=50,
                aspect_ratio=aspect_ratio,
                progress_callback=update_render_progress,
            )

            if success:
                job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path), progress=100)
            else:
                job_manager.update_job(job_id, JobStatus.FAILED, error="FFmpeg video generation failed.")
        finally:
            loop.close()

    def _process_shorts_job(self, job_id: str, payload: Dict[str, Any]):
        logger.info(f"Starting Shorts processing for job {job_id}")
        target_lang = payload.get("target_lang", "vi")
        prompt = (payload.get("prompt") or "").strip()
        script_input = (payload.get("script") or "").strip()
        voice_id = payload.get("voice_id", "vi-VN-HoaiMyNeural")
        duration_seconds = int(payload.get("duration_seconds") or 0)
        aspect_ratio = payload.get("aspect_ratio", "9:16")
        video_engine = payload.get("video_engine", "local")

        self._check_pause_and_cancel(job_id)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 1/3: Building the script...", progress=5)
        script = ScriptService.resolve_shorts_script(prompt, script_input, target_lang)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 1/3: Script ready.", progress=30)

        # Step 2/3: TTS
        self._check_pause_and_cancel(job_id)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 2/3: Generating voiceover (TTS)...", progress=35)
        import asyncio
        loop = asyncio.new_event_loop()

        try:
            tts_service = TTSService(voice=voice_id, target_lang=target_lang)
            audio_path, srt_path = loop.run_until_complete(
                tts_service.generate_audio_with_subtitles(script, target_lang, job_id)
            )
            audio_path = loop.run_until_complete(self._maybe_mix_bgm(job_id, audio_path))

            if duration_seconds > 0:
                stretched_audio = settings.TEMP_DIR / f"{job_id}_tts_stretched.wav"
                if VideoService.stretch_audio(audio_path, stretched_audio, duration_seconds):
                    audio_path = stretched_audio
                else:
                    logger.warning("Could not stretch audio to %ss for job %s", duration_seconds, job_id)

            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 2/3: Voiceover generated.", progress=70)

            # Step 3/3: Render
            self._check_pause_and_cancel(job_id)
            output_filename = f"{job_id}_shorts.mp4"
            output_path = settings.OUTPUT_DIR / output_filename
            if video_engine == "local":
                job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 3/3: Rendering short...", progress=75)
                width, height = VideoService._canvas_size(aspect_ratio)
                background_path = settings.TEMP_DIR / f"{job_id}_bg.png"
                background_path.parent.mkdir(parents=True, exist_ok=True)
                VideoService.create_gradient_background(background_path, width, height)

                def update_render_progress(ratio: float):
                    progress = 75 + (ratio * 23)
                    job_manager.update_job(
                        job_id,
                        JobStatus.PROCESSING,
                        message=f"Step 3/3: Rendering short... {int(ratio * 100)}%",
                        progress=round(progress, 1),
                    )

                success = VideoService.image_audio_to_video(
                    image_path=background_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    srt_path=srt_path,
                    font_size=56,
                    aspect_ratio=aspect_ratio,
                    progress_callback=update_render_progress,
                )
            else:
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=f"Step 3/3: Generating video with {video_engine}...",
                    progress=75,
                )
                video_prompt = prompt or script
                video_prompt = video_prompt[:800]
                temp_video = settings.TEMP_DIR / f"{job_id}_{video_engine}.mp4"
                video_service = VideoGenService()
                generated_path = video_service.generate_fal_video(
                    provider=video_engine,
                    prompt=video_prompt,
                    output_path=temp_video,
                    aspect_ratio=aspect_ratio,
                    duration_seconds=duration_seconds,
                )

                video_duration = VideoService.get_duration(generated_path)
                if video_duration > 0:
                    stretched_audio = settings.TEMP_DIR / f"{job_id}_tts_stretched.wav"
                    if VideoService.stretch_audio(audio_path, stretched_audio, video_duration):
                        audio_path = stretched_audio

                def update_merge_progress(ratio: float):
                    progress = 85 + (ratio * 13)
                    job_manager.update_job(
                        job_id,
                        JobStatus.PROCESSING,
                        message=f"Step 3/3: Final mix... {int(ratio * 100)}%",
                        progress=round(progress, 1),
                    )

                success = VideoService.merge_audio_video(
                    video_path=generated_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    srt_path=srt_path,
                    progress_callback=update_merge_progress,
                )

            if success:
                job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path), progress=100)
            else:
                job_manager.update_job(job_id, JobStatus.FAILED, error="FFmpeg video generation failed.")
        finally:
            loop.close()

    def _process_dubbing_job(self, job_id: str, payload: Dict[str, Any]):
        """Execute the dubbing pipeline with cancel/pause checkpoints and progress tracking."""
        target_lang = payload.get("target_lang", "vi")
        source_path = payload.get("source_path")

        # Step 0: Download if URL (0% -> 10%)
        if isinstance(source_path, str) and (source_path.startswith("http") or "drive.google.com" in source_path):
            self._check_pause_and_cancel(job_id)
            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 1/6: Downloading video from URL...", progress=2)
            url_service = URLService()
            source_path = url_service.download_video(source_path)
            job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 1/6: Download complete.", progress=10)

        # Step 1: Extract audio (10% -> 20%)
        self._check_pause_and_cancel(job_id)
        job_manager.update_job(job_id, JobStatus.PROCESSING, message="Step 2/6: Extracting audio from video...", progress=12)

        pipeline = DubbingPipeline(target_lang=target_lang)
        pipeline.video_service = VideoService()
        pipeline.asr_service = ASRService()
        pipeline.translate_service = TranslateService(
            target_lang=target_lang,
            service_type=settings.default_translation_service(),
        )
        pipeline.tts_service = TTSService(
            voice=TTSService.default_voice_for_lang(target_lang),
            target_lang=target_lang,
        )

        import asyncio
        import os
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()

        def _translate_progress(done: int, total: int) -> None:
            if total <= 0:
                return
            job_manager.update_job(
                job_id,
                JobStatus.PROCESSING,
                message=f"Step 4/6: Translating text... ({done}/{total})",
                progress=round(42 + ((done / total) * 13), 1),
            )

        def _tts_progress(done: int, total: int) -> None:
            if total <= 0:
                return
            job_manager.update_job(
                job_id,
                JobStatus.PROCESSING,
                message=f"Step 5/6: Generating dubbed audio (TTS)... ({done}/{total})",
                progress=round(57 + ((done / total) * 23), 1),
            )

        reporter = CallbackDubbingReporter(
            check_cancel=lambda: self._check_cancelled(job_id),
            check_pause=lambda: self._check_pause_and_cancel(job_id),
            stage=lambda message, progress: job_manager.update_job(
                job_id, JobStatus.PROCESSING, message=message, progress=progress
            ),
            translate_progress=_translate_progress,
            tts_progress=_tts_progress,
            merge_progress=lambda ratio: job_manager.update_job(
                job_id,
                JobStatus.PROCESSING,
                message=f"Step 6/6: Merging audio and video... {int(ratio * 100)}%",
                progress=round(82 + (ratio * 13), 1),
            ),
        )

        try:
            output_path = loop.run_until_complete(
                pipeline.run(Path(str(source_path)), job_id, reporter=reporter)
            )
            job_manager.update_job(
                job_id, JobStatus.COMPLETED, output_path=str(output_path), progress=100
            )
        except CancelledError:
            raise
        except Exception as e:
            logger.error("Dubbing failed for %s: %s", job_id, e)
            job_manager.update_job(job_id, JobStatus.FAILED, error=str(e))
        finally:
            loop.close()



# Global worker instance
worker = BackgroundWorker()
