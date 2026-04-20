import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.video_service import VideoService
from app.services.asr_service import ASRService
from app.services.translate_service import TranslateService
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

class DubbingPipeline:
    def __init__(self, target_lang: str = "vi", whisper_model: str = "base"):
        self.target_lang = target_lang
        self.video_service = VideoService()
        self.asr_service = ASRService(model_size=whisper_model)
        self.translate_service = TranslateService(target_lang=target_lang)
        self.tts_service = TTSService()

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

            # 3. Transcribe & Merge
            logger.info("Step 2/5: Transcribing...")
            raw_segments = self.asr_service.transcribe(orig_audio)
            merged_segments = self.asr_service.merge_segments_by_sentence(raw_segments)
            self.asr_service.save_transcript(merged_segments, transcript_path)

            # 4. Translate
            logger.info(f"Step 3/5: Translating to {self.target_lang}...")
            translated_segments = self.translate_service.translate_batch(merged_segments)

            # 5. TTS & Alignment
            logger.info("Step 4/5: Generating TTS and aligning...")
            audio_segments = await self.tts_service.process_segments(translated_segments, session_dir)
            
            # 6. Merge Back
            logger.info("Step 5/5: Merging results...")
            self.tts_service.create_concat_list(audio_segments, translated_segments, concat_list_path)
            
            if not self.video_service.concat_audio_segments(concat_list_path, final_audio):
                raise Exception("Failed to concatenate audio segments")
            
            if not self.video_service.merge_audio_video(video_path, final_audio, output_video):
                raise Exception("Failed to merge audio and video")

            logger.info(f"Pipeline completed successfully! Output: {output_video}")
            return output_video

        except Exception as e:
            logger.error(f"Pipeline failed for session {session_id}: {e}")
            return None
        finally:
            # Optional: cleanup session_dir
            pass
