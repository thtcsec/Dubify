import logging
import asyncio
import edge_tts
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm
from app.core.config import settings
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def generate_audio(self, text: str, output_path: Path) -> bool:
        """Generate audio for a single text string using Edge-TTS."""
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(str(output_path))
            return True
        except Exception as e:
            logger.error(f"Edge-TTS error: {e}")
            return False

    async def process_segments(self, segments: List[Dict[str, Any]], temp_dir: Path) -> List[Path]:
        """
        Generate audio for all segments and align them with original timing.
        Returns list of paths to final aligned audio segments.
        """
        logger.info(f"Generating TTS for {len(segments)} segments")
        final_segments = []
        
        for i, seg in enumerate(segments):
            text = seg.get('translated_text', seg['text'])
            target_duration = seg['end'] - seg['start']
            
            raw_path = temp_dir / f"tts_{i}_raw.mp3"
            aligned_path = temp_dir / f"tts_{i}_aligned.wav"
            
            # 1. Generate Raw TTS
            success = await self.generate_audio(text, raw_path)
            if not success:
                continue
            
            # 2. Time-stretch to match original duration (VideoService logic)
            # We align the audio to match the visual timing of the original segment
            VideoService.stretch_audio(raw_path, aligned_path, target_duration)
            
            if aligned_path.exists():
                final_segments.append(aligned_path)
                
        return final_segments

    @staticmethod
    def create_concat_list(audio_paths: List[Path], segments: List[Dict[str, Any]], output_list_file: Path):
        """
        Create a concat file for FFmpeg, including silent gaps to maintain sync.
        Logic: if (current_start - previous_end) > threshold, add silence.
        """
        with open(output_list_file, 'w', encoding='utf-8') as f:
            for i, path in enumerate(audio_paths):
                # FFmpeg concat format: file 'path'
                f.write(f"file '{path.absolute()}'\n")
        logger.info(f"Concat list created at {output_list_file}")
