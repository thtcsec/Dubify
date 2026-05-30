import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.asr_service import ASRService
from app.services.dubbing_reporter import DubbingReporter, NullDubbingReporter
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService
from app.services.video_service import VideoService
from app.utils.artifacts import persist_dubbing_artifacts
from app.utils.safe_filename import dubbed_output_filename
from app.utils.subtitles import chunks_to_srt

logger = logging.getLogger(__name__)


class DubbingPipeline:
    def __init__(self, target_lang: str = "vi", whisper_model: str = "base"):
        self.target_lang = target_lang
        self.video_service = VideoService()
        self.asr_service = ASRService(model_size=whisper_model)
        self.translate_service = TranslateService(target_lang=target_lang)
        self.tts_service = TTSService(
            voice=TTSService.default_voice_for_lang(target_lang),
            target_lang=target_lang,
        )

    async def run(
        self,
        video_path: Path,
        session_id: str,
        reporter: Optional[DubbingReporter] = None,
    ) -> Path:
        """
        Video -> Audio -> ASR -> Translate -> TTS -> merge -> output video.
        Raises on failure; caller handles job status updates.
        """
        report = reporter or NullDubbingReporter()
        session_dir = settings.TEMP_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        orig_audio = session_dir / "original_audio.wav"
        transcript_path = session_dir / "transcript.json"
        concat_list_path = session_dir / "concat_list.txt"
        final_audio = session_dir / "dubbed_audio_final.wav"
        output_video = settings.OUTPUT_DIR / dubbed_output_filename(session_id, video_path.name)

        try:
            report.check_cancel()
            report.stage("Step 2/6: Extracting audio from video...", 12)
            if not self.video_service.extract_audio(video_path, orig_audio):
                raise RuntimeError("Failed to extract audio")

            asr_input_audio = orig_audio
            bgm_audio = None
            if settings.ENABLE_BGM_RETENTION:
                logger.info("BGM retention enabled — separating vocals and BGM...")
                vocals_path, bgm_path = self.video_service.separate_audio_demucs(orig_audio, session_dir)
                if vocals_path and bgm_path:
                    asr_input_audio = vocals_path
                    bgm_audio = bgm_path
                else:
                    logger.warning("Demucs separation unavailable; using original audio.")

            report.stage("Step 2/6: Audio extracted.", 20)

            report.check_pause()
            report.stage("Step 3/6: Transcribing audio (ASR)...", 22)
            raw_segments = await asyncio.to_thread(self.asr_service.transcribe, asr_input_audio)
            if not raw_segments:
                raise RuntimeError(
                    "Transcription returned no segments. The audio may be silent or corrupted."
                )
            merged_segments = await asyncio.to_thread(
                self.asr_service.merge_segments_by_sentence, raw_segments
            )
            merged_segments = await asyncio.to_thread(
                self.asr_service.split_oversized_segments, merged_segments
            )
            await asyncio.to_thread(self.asr_service.save_transcript, merged_segments, transcript_path)
            report.stage("Step 3/6: Transcription complete.", 40)

            report.check_pause()
            report.stage("Step 4/6: Translating text...", 42)
            translated_segments = await asyncio.to_thread(
                self.translate_service.translate_batch,
                merged_segments,
                5,
                report.translate_progress,
            )
            if translated_segments:
                sample = translated_segments[0]
                logger.info(
                    "Translation target=%s via %s — sample: '%s' -> '%s'",
                    self.target_lang,
                    self.translate_service.service_type,
                    (sample.get("text") or "")[:80],
                    (sample.get("translated_text") or "")[:80],
                )

            if settings.F5TTS_API_URL:
                await self._extract_voice_slices(translated_segments, asr_input_audio, session_dir)
                self.tts_service.provider = "f5tts"

            report.stage("Step 4/6: Translation complete.", 55)

            report.check_pause()
            report.stage("Step 5/6: Generating dubbed audio (TTS)...", 57)
            audio_segments = await self.tts_service.process_segments(
                translated_segments,
                session_dir,
                progress_callback=report.tts_progress,
            )

            srt_path = session_dir / "translated.srt"
            srt_path.write_text(chunks_to_srt(translated_segments), encoding="utf-8")
            report.stage("Step 5/6: Audio generated.", 80)

            report.check_pause()
            report.stage("Step 6/6: Merging audio and video...", 82)
            self.tts_service.create_concat_list(
                audio_segments, translated_segments, concat_list_path, session_dir
            )
            if not self.video_service.concat_audio_segments(concat_list_path, final_audio):
                raise RuntimeError("Failed to concatenate audio segments")

            final_audio_with_bgm = await self._mix_bgm_if_needed(final_audio, bgm_audio, session_dir)

            if not self.video_service.merge_audio_video(
                video_path,
                final_audio_with_bgm,
                output_video,
                srt_path,
                progress_callback=report.merge_progress,
            ):
                raise RuntimeError("Failed to merge audio and video")

            persist_dubbing_artifacts(session_id, session_dir, source_video=video_path)
            report.stage("Step 6/6: Finalizing...", 95)
            logger.info("Pipeline completed: %s", output_video)
            return output_video
        finally:
            if settings.CLEANUP_TEMP:
                shutil.rmtree(session_dir, ignore_errors=True)

    async def _extract_voice_slices(
        self,
        segments: list,
        asr_input_audio: Path,
        session_dir: Path,
    ) -> None:
        logger.info("Extracting audio slices for voice cloning reference...")
        slices_dir = session_dir / "slices"
        slices_dir.mkdir(exist_ok=True)
        for i, seg in enumerate(segments):
            slice_path = slices_dir / f"slice_{i}.wav"
            cut_cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(seg["start"]),
                "-t",
                str(seg["end"] - seg["start"]),
                "-i",
                str(asr_input_audio),
                "-c:a",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(slice_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cut_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
                if proc.returncode != 0:
                    logger.warning(
                        "FFmpeg slicing failed: %s", stderr.decode(errors="ignore")
                    )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("FFmpeg slicing timed out for segment %d", i)
            if slice_path.exists():
                seg["ref_audio"] = str(slice_path)

    async def _mix_bgm_if_needed(
        self,
        final_audio: Path,
        bgm_audio: Optional[Path],
        session_dir: Path,
    ) -> Path:
        if not bgm_audio:
            return final_audio

        logger.info("Mixing BGM with dubbed audio...")
        mixed_audio = session_dir / "dubbed_audio_with_bgm.wav"
        mix_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(final_audio),
            "-i",
            str(bgm_audio),
            "-filter_complex",
            "[1:a]volume=0.15[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
            "-map",
            "[aout]",
            "-ac",
            "2",
            str(mixed_audio),
        ]
        proc = await asyncio.create_subprocess_exec(
            *mix_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
            if proc.returncode != 0:
                logger.warning("BGM mixing failed: %s", stderr.decode(errors="ignore"))
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            logger.warning("BGM mixing timed out")
        if mixed_audio.exists() and mixed_audio.stat().st_size > 0:
            return mixed_audio
        return final_audio
