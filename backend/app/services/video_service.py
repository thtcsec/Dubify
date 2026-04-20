import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class VideoService:
    @staticmethod
    def extract_audio(video_path: Path, output_path: Path, sample_rate: int = 16000) -> bool:
        """Extract mono audio from video file."""
        try:
            logger.info(f"Extracting audio from {video_path}")
            command = [
                "ffmpeg", "-y", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le",
                "-ar", str(sample_rate), "-ac", "1", 
                str(output_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg extraction error: {e.stderr.decode()}")
            return False

    @staticmethod
    def get_duration(file_path: Path) -> float:
        """Get duration of a media file using ffprobe."""
        try:
            command = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting duration for {file_path}: {e}")
            return 0.0

    @staticmethod
    def stretch_audio(input_file: Path, output_file: Path, target_duration: float) -> bool:
        """Stretch or compress audio to match target duration using FFmpeg atempo."""
        try:
            current_duration = VideoService.get_duration(input_file)
            if current_duration <= 0:
                return False
            
            ratio = current_duration / target_duration
            
            # FFmpeg atempo only supports 0.5 to 2.0. We may need to chain them.
            filters = []
            temp_ratio = ratio
            while temp_ratio > 2.0:
                filters.append("atempo=2.0")
                temp_ratio /= 2.0
            while temp_ratio < 0.5:
                filters.append("atempo=0.5")
                temp_ratio /= 0.5
            filters.append(f"atempo={temp_ratio:.4f}")
            
            filter_str = ",".join(filters)
            
            command = [
                "ffmpeg", "-y", "-i", str(input_file),
                "-filter:a", filter_str,
                str(output_file)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio stretch error: {e.stderr.decode()}")
            return False

    @staticmethod
    def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path) -> bool:
        """Replace original audio with new audio track."""
        try:
            logger.info(f"Merging {audio_path} into {video_path}")
            # -map 0:v:0 -> use video from first input
            # -map 1:a:0 -> use audio from second input
            # -c:v copy -> don't re-encode video (fast)
            # -shortest -> end when shortest stream ends
            command = [
                "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", str(output_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Merging error: {e.stderr.decode()}")
            return False

    @staticmethod
    def concat_audio_segments(segment_list_file: Path, output_file: Path) -> bool:
        """Concatenate multiple audio segments using FFmpeg concat demuxer."""
        try:
            command = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(segment_list_file),
                "-c", "copy", str(output_file)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Concat error: {e.stderr.decode()}")
            return False
