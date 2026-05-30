"""
Background Worker with cancel/pause awareness.

The worker checks job_manager.is_cancelled() and job_manager.wait_if_paused()
between pipeline steps so jobs can be interrupted gracefully.
"""

import threading
import queue
import logging
import asyncio
import shutil
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
        studio_visual_mode = (payload.get("studio_visual_mode") or "html_scenes").strip().lower()
        studio_template = (payload.get("studio_template") or settings.STUDIO_DEFAULT_TEMPLATE).strip()
        studio_render_engine = (payload.get("studio_render_engine") or "auto").strip().lower()
        social_overlay_payload = {
            "social_overlay": payload.get("social_overlay", "none"),
            "social_handle": payload.get("social_handle", ""),
            "social_subtitle": payload.get("social_subtitle", ""),
            "social_avatar_path": payload.get("social_avatar_path"),
        }
        studio_layout_payload = {
            "header_y_pct": payload.get("header_y_pct"),
            "footer_y_pct": payload.get("footer_y_pct"),
            "social_left_pct": payload.get("social_left_pct"),
            "social_bottom_pct": payload.get("social_bottom_pct"),
            "caption_y_pct": payload.get("caption_y_pct"),
        }

        from app.utils.studio_background import ensure_studio_background

        bg_path = ensure_studio_background(job_id, aspect_ratio, image_path=image_path)

        self._check_pause_and_cancel(job_id)
        step1_msg = "Step 1/3: Preparing script..." if use_raw_script else "Step 1/3: Rewriting script with LLM..."
        job_manager.update_job(job_id, JobStatus.PROCESSING, message=step1_msg, progress=5)
        try:
            script = ScriptService.resolve_studio_script(raw_text, target_lang, use_raw_script=use_raw_script)
        except ValueError as script_err:
            job_manager.update_job(job_id, JobStatus.FAILED, error=str(script_err), progress=0)
            return
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
                tts_service.generate_studio_audio_with_subtitles(script, target_lang, job_id)
            )
            audio_path = loop.run_until_complete(self._maybe_mix_bgm(job_id, audio_path))
            loop.close()
            asyncio.set_event_loop(None)

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
            from app.utils.project_title import derive_studio_title
            from app.utils.safe_filename import studio_output_filename

            title = derive_studio_title(
                project_name=str(payload.get("project_name") or ""),
                research_topic=str(payload.get("research_topic") or ""),
                script=script,
            )
            output_filename = studio_output_filename(job_id, title)
            output_path = settings.OUTPUT_DIR / output_filename
            def update_render_progress(ratio: float):
                progress = 75 + (ratio * 23)
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=f"Step 3/3: Rendering final video... {int(ratio * 100)}%",
                    progress=round(progress, 1),
                )

            allowed_templates = {"tiktok_news", "tiktok_news_pill", "news_scene", "pixelle_story"}
            if studio_template not in allowed_templates:
                studio_template = settings.STUDIO_DEFAULT_TEMPLATE
            use_scene_images = payload.get("use_scene_images")
            if use_scene_images is None:
                use_scene_images = settings.STUDIO_USE_SCENE_IMAGES

            success = False
            if studio_visual_mode == "html_scenes":
                from app.services.studio_video_builder import build_html_scene_video

                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message="Step 3/3: Rendering HTML scene slides...",
                    progress=76,
                )
                success = build_html_scene_video(
                    script=script,
                    image_path=bg_path,
                    audio_path=audio_path,
                    subtitle_path=srt_path,
                    output_path=output_path,
                    aspect_ratio=aspect_ratio,
                    template_name=studio_template,
                    social_overlay=social_overlay_payload,
                    studio_layout=studio_layout_payload,
                    render_engine=studio_render_engine,
                    progress_callback=update_render_progress,
                    research_topic=payload.get("research_topic") or None,
                    wiki_thumbnail_url=str(payload.get("wiki_thumbnail_url") or ""),
                    use_scene_images=bool(use_scene_images),
                )
                if not success:
                    logger.warning("HTML scene render failed for %s; using classic Ken Burns.", job_id)

            if not success:
                success = VideoService.image_audio_to_video(
                    image_path=bg_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    srt_path=srt_path,
                    font_size=56,
                    aspect_ratio=aspect_ratio,
                    progress_callback=update_render_progress,
                )

            if success:
                from app.utils.studio_overlay import branding_active, parse_studio_branding, parse_studio_layout

                branding = parse_studio_branding(payload)
                layout = parse_studio_layout(payload, aspect_ratio=aspect_ratio)
                if branding_active(branding):
                    branded = settings.TEMP_DIR / f"{job_id}_branded.mp4"
                    if VideoService.apply_studio_branding(
                        output_path, branded, aspect_ratio, branding, layout
                    ):
                        shutil.move(str(branded), str(output_path))
                job_manager.update_job(job_id, JobStatus.COMPLETED, output_path=str(output_path), progress=100)
            else:
                job_manager.update_job(job_id, JobStatus.FAILED, error="FFmpeg video generation failed.")
        finally:
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

    def _process_shorts_job(self, job_id: str, payload: Dict[str, Any]):
        """Fetch long video → ASR → translate → dub → cut into Part 1, Part 2, …"""
        logger.info("Starting Shorts repurpose for job %s", job_id)
        target_lang = payload.get("target_lang", "vi")
        voice_id = payload.get("voice_id") or TTSService.default_voice_for_lang(target_lang)
        video_url = (payload.get("video_url") or "").strip()
        video_path = payload.get("video_path")
        max_part_duration = float(payload.get("max_part_duration") or 60)
        vertical_crop = bool(payload.get("vertical_crop", True))

        source_path = str(video_path) if video_path else None
        if not source_path and not video_url:
            job_manager.update_job(
                job_id, JobStatus.FAILED, error="Provide a video URL or upload a file.", progress=0
            )
            return

        import asyncio

        if os.name == "nt":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()

        try:
            if not source_path:
                self._check_pause_and_cancel(job_id)
                job_manager.update_job(
                    job_id, JobStatus.PROCESSING, message="Step 1/7: Downloading video…", progress=2
                )
                source_path = str(URLService().download_video(video_url))
                job_manager.update_job(
                    job_id, JobStatus.PROCESSING, message="Step 1/7: Download complete.", progress=8
                )

            pipeline = DubbingPipeline(target_lang=target_lang)
            pipeline.video_service = VideoService()
            pipeline.asr_service = ASRService(model_size=settings.DEFAULT_WHISPER_MODEL)
            pipeline.translate_service = TranslateService(
                target_lang=target_lang,
                service_type=settings.default_translation_service(),
            )
            pipeline.tts_service = TTSService(voice=voice_id, target_lang=target_lang)

            def _translate_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=f"Step 4/7: Translating… ({done}/{total})",
                    progress=round(38 + ((done / total) * 12), 1),
                )

            def _tts_progress(done: int, total: int) -> None:
                if total <= 0:
                    return
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=f"Step 5/7: Dubbing voice (TTS)… ({done}/{total})",
                    progress=round(52 + ((done / total) * 20), 1),
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
                    message=f"Step 6/7: Merging dubbed video… {int(ratio * 100)}%",
                    progress=round(74 + (ratio * 10), 1),
                ),
            )

            dubbed_path = loop.run_until_complete(
                pipeline.run(Path(source_path), job_id, reporter=reporter)
            )
            loop.close()
            asyncio.set_event_loop(None)

            from app.services.shorts_repurpose_service import export_dubbed_shorts_parts

            def export_progress(ratio: float, msg: str) -> None:
                job_manager.update_job(
                    job_id,
                    JobStatus.PROCESSING,
                    message=msg,
                    progress=round(84 + ratio * 14, 1),
                )

            job_manager.update_job(
                job_id,
                JobStatus.PROCESSING,
                message="Step 7/7: Cutting Part 1, Part 2…",
                progress=85,
            )
            parts = export_dubbed_shorts_parts(
                job_id,
                Path(dubbed_path),
                max_part_duration=max_part_duration,
                vertical_crop=vertical_crop,
                progress_callback=export_progress,
            )

            if not parts:
                job_manager.update_job(
                    job_id,
                    JobStatus.FAILED,
                    error="Dubbing succeeded but could not export short parts.",
                    progress=0,
                )
                return

            job_manager.update_job(
                job_id,
                JobStatus.COMPLETED,
                output_path=Path(dubbed_path).name,
                parts=parts,
                message=f"Done — {len(parts)} part(s) ready (dubbed + cut).",
                progress=100,
            )
        except CancelledError:
            raise
        except Exception as e:
            logger.error("Shorts repurpose failed for %s: %s", job_id, e)
            job_manager.update_job(job_id, JobStatus.FAILED, error=str(e), progress=0)
        finally:
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception:
                pass
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

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
        pipeline.asr_service = ASRService(
            model_size=settings.DEFAULT_WHISPER_MODEL,
        )
        pipeline.translate_service = TranslateService(
            target_lang=target_lang,
            service_type=settings.default_translation_service(),
        )
        dub_voice = payload.get("voice_id") or TTSService.default_voice_for_lang(target_lang)
        pipeline.tts_service = TTSService(voice=dub_voice, target_lang=target_lang)

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
