import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService
from app.utils.subtitles import chunks_to_srt

logger = logging.getLogger(__name__)

class DubbingPipeline:
    def __init__(self, target_lang: str = "vi", whisper_model: str = "base"):
        self.target_lang = target_lang
        self.video_service = VideoService()
        self.asr_service = ASRService(model_size=whisper_model)
        self.translate_service = TranslateService(target_lang=target_lang)
        self.tts_service = TTSService(target_lang=target_lang)

    async def run(self, video_path: Path, session_id: str) -> Optional[Path]:
        """
        Run the full dubbing pipeline:
        Video -> Audio -> Transcription -> Translation -> TTS -> Aligned Audio -> Final Video
        """
        # 1. Setup workspace
        session_dir = settings.TEMP_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        orig_audio = session_dir / "original_audio.wav"
        transcript_path = session_dir / "transcript.json"
        concat_list_path = session_dir / "concat_list.txt"
        final_audio = session_dir / "dubbed_audio_final.wav"
        output_video = settings.OUTPUT_DIR / f"dubbed_{video_path.name}"

        try:
            # 2. Extract Audio
            logger.info("Step 1/5: Extracting audio...")
            if not self.video_service.extract_audio(video_path, orig_audio):
                raise Exception("Failed to extract audio")

            asr_input_audio = orig_audio
            bgm_audio = None
            if settings.ENABLE_BGM_RETENTION:
                logger.info("BGM Retention enabled. Separating vocals and BGM...")
                vocals_path, bgm_path = self.video_service.separate_audio_demucs(orig_audio, session_dir)
                if vocals_path and bgm_path:
                    asr_input_audio = vocals_path
                    bgm_audio = bgm_path
                else:
                    logger.warning("Demucs separation failed or not installed. Falling back to original audio.")

            # 3. Transcribe & Merge
            logger.info("Step 2/5: Transcribing...")
            raw_segments = self.asr_service.transcribe(asr_input_audio)
            if not raw_segments:
                raise Exception("Transcription returned no segments. The audio may be silent or corrupted.")
            merged_segments = self.asr_service.merge_segments_by_sentence(raw_segments)
            self.asr_service.save_transcript(merged_segments, transcript_path)

            # 4. Translate
            logger.info("Step 3/5: Translating %d segments to %s...", len(merged_segments), self.target_lang)
            translated_segments = self.translate_service.translate_batch(merged_segments)

            # Extract audio slices for voice cloning if F5-TTS is enabled
            if settings.F5TTS_API_URL:
                logger.info("Extracting audio slices for voice cloning reference...")
                slices_dir = session_dir / "slices"
                slices_dir.mkdir(exist_ok=True)
                for i, seg in enumerate(translated_segments):
                    slice_path = slices_dir / f"slice_{i}.wav"
                    start_str = str(seg['start'])
                    duration_str = str(seg['end'] - seg['start'])
                    cut_cmd = [
                        "ffmpeg", "-y", "-ss", start_str, "-t", duration_str,
                        "-i", str(asr_input_audio), "-c", "copy", str(slice_path)
                    ]
                    subprocess.run(cut_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
                    if slice_path.exists():
                        seg['ref_audio'] = str(slice_path)
            
            # Setup TTS provider
            if settings.F5TTS_API_URL:
                self.tts_service.provider = "f5tts"

            # 5. TTS & Alignment
            logger.info("Step 4/5: Generating TTS and formatting subtitles...")
            audio_segments = await self.tts_service.process_segments(translated_segments, session_dir)
            
            # Generate SRT from translated segments
            srt_content = chunks_to_srt(translated_segments)
            srt_path = session_dir / "translated.srt"
            srt_path.write_text(srt_content, encoding="utf-8")
            
            # 6. Merge Back & Burn Subtitles
            logger.info("Step 5/5: Merging results and burning subtitles...")
            self.tts_service.create_concat_list(audio_segments, translated_segments, concat_list_path, session_dir)
            
            if not self.video_service.concat_audio_segments(concat_list_path, final_audio):
                raise Exception("Failed to concatenate audio segments")
            
            # Mix BGM back in if enabled
            final_audio_with_bgm = final_audio
            if bgm_audio:
                logger.info("Mixing BGM with dubbed audio...")
                mixed_audio = session_dir / "dubbed_audio_with_bgm.wav"
                mix_cmd = [
                    "ffmpeg", "-y", "-i", str(final_audio), "-i", str(bgm_audio),
                    "-filter_complex", "amix=inputs=2:duration=first:dropout_transition=3",
                    str(mixed_audio)
                ]
                try:
                    subprocess.run(mix_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
                except subprocess.CalledProcessError as e:
                    logger.warning("BGM mixing failed: %s. Continuing without BGM.", e.stderr.decode() if e.stderr else str(e))
                if mixed_audio.exists() and mixed_audio.stat().st_size > 0:
                    final_audio_with_bgm = mixed_audio
            
            if not self.video_service.merge_audio_video(video_path, final_audio_with_bgm, output_video, srt_path):
                raise Exception("Failed to merge audio and video")

            logger.info("Pipeline completed successfully! Output: %s", output_video)
            return output_video

        except Exception as e:
            logger.error("Pipeline failed for session %s: %s", session_id, e, exc_info=True)
            return None
