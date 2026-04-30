import subprocess
import os
import shutil
import logging
import tempfile
import re
from pathlib import Path
from typing import Optional, Tuple, Callable
import numpy as np
from PIL import Image
from app.core.config import settings

logger = logging.getLogger(__name__)

class VideoService:
    ASPECT_RATIOS = {
        "16:9": (1920, 1080),
        "4:3": (1440, 1080),
        "9:16": (1080, 1920),
        "3:4": (1080, 1440),
        "1:1": (1080, 1080),
    }

    @staticmethod
    def _ffmpeg_subtitle_path(path: Path) -> str:
        normalized = str(path.resolve()).replace("\\", "/")
        if len(normalized) >= 2 and normalized[1] == ":":
            normalized = f"{normalized[0]}\\:{normalized[2:]}"
        return normalized.replace("'", "\\'")

    @staticmethod
    def _canvas_size(aspect_ratio: str) -> Tuple[int, int]:
        return VideoService.ASPECT_RATIOS.get(aspect_ratio, VideoService.ASPECT_RATIOS["16:9"])

    @staticmethod
    def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
        cleaned = value.lstrip("#")
        if len(cleaned) != 6:
            return (12, 18, 38)
        return tuple(int(cleaned[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def create_gradient_background(
        output_path: Path,
        width: int,
        height: int,
        top_color: str = "#0b1020",
        bottom_color: str = "#1f2a44",
    ) -> Path:
        """Create a simple vertical gradient background image."""
        start = np.array(VideoService._hex_to_rgb(top_color), dtype=np.float32)
        end = np.array(VideoService._hex_to_rgb(bottom_color), dtype=np.float32)
        # Create gradient column (height, 1, 3)
        gradient = np.linspace(0, 1, height, dtype=np.float32).reshape(height, 1, 1)
        column = (start + (end - start) * gradient).astype(np.uint8)  # (height, 1, 3)
        # Tile across width to get (height, width, 3)
        image_array = np.tile(column, (1, width, 1))
        Image.fromarray(image_array).save(output_path)
        return output_path

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        total_cs = int(max(seconds, 0) * 100)
        hours = total_cs // 360000
        minutes = (total_cs % 360000) // 6000
        secs = (total_cs % 6000) // 100
        centis = total_cs % 100
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    @staticmethod
    def _escape_ass_text(text: str) -> str:
        escaped = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        escaped = escaped.replace("\n", r"\N")
        return escaped

    @staticmethod
    def _parse_vtt(vtt_path: Path) -> list[tuple[float, float, str]]:
        cues: list[tuple[float, float, str]] = []
        content = vtt_path.read_text(encoding="utf-8", errors="ignore")
        blocks = re.split(r"\r?\n\r?\n", content.strip())

        def parse_ts(value: str) -> float:
            hh, mm, rest = value.split(":")
            ss, ms = rest.split(".")
            return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines or lines[0].upper() == "WEBVTT":
                continue
            time_line_index = 0 if "-->" in lines[0] else 1
            if time_line_index >= len(lines) or "-->" not in lines[time_line_index]:
                continue
            start_str, end_str = [part.strip().split(" ")[0] for part in lines[time_line_index].split("-->")]
            text = " ".join(lines[time_line_index + 1:]).strip()
            if text:
                cues.append((parse_ts(start_str), parse_ts(end_str), text))
        return cues

    @staticmethod
    def _create_pop_ass(vtt_path: Path, output_path: Path, canvas_size: Tuple[int, int]) -> Path:
        width, height = canvas_size
        font_size = max(42, int(min(width, height) * 0.055))
        cues = VideoService._parse_vtt(vtt_path)
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            f"Style: Pop,Arial,{font_size},&H00FFFFFF,&H0000F0FF,&H00111111,&H66000000,-1,0,0,0,100,100,0,0,1,3,0,2,80,80,{max(70, int(height * 0.08))},1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]

        for start, end, text in cues:
            animated = r"{\fad(60,90)\fscx82\fscy82\t(0,180,\fscx100\fscy100)\blur0.4}"
            lines.append(
                f"Dialogue: 0,{VideoService._format_ass_time(start)},{VideoService._format_ass_time(end)},Pop,,0,0,0,,{animated}{VideoService._escape_ass_text(text)}"
            )

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

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
    def _run_ffmpeg_with_progress(command: list[str], duration: float, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        if progress_callback is None or duration <= 0:
            try:
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg progress run error: {e.stderr.decode()}")
                return False

        progress_command = command[:-1] + ["-progress", "pipe:1", "-nostats", command[-1]]
        process = subprocess.Popen(
            progress_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        last_ratio = 0.0
        try:
            assert process.stdout is not None
            for line in process.stdout:
                line = line.strip()
                if not line.startswith("out_time_ms="):
                    continue
                try:
                    out_time_ms = int(line.split("=", 1)[1])
                except ValueError:
                    continue
                ratio = min(max(out_time_ms / 1_000_000 / duration, 0.0), 1.0)
                if ratio > last_ratio:
                    last_ratio = ratio
                    progress_callback(ratio)
            stderr_output = process.stderr.read() if process.stderr else ""
            if process.wait() != 0:
                logger.error(f"FFmpeg progress run error: {stderr_output}")
                return False
            progress_callback(1.0)
            return True
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

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

            if target_duration <= 0:
                return False
            if abs(ratio - 1.0) < 0.03:
                shutil.copyfile(input_file, output_file)
                return True

            # FFmpeg atempo only supports 0.5 to 2.0, but Rubberband handles arbitrary values better
            # Use rubberband filter if available, fallback to atempo if not (rubberband is much higher quality)
            # FFmpeg standard command for rubberband: rubberband=tempo=X
            filter_str = f"rubberband=tempo={ratio:.4f}"
            
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
    def merge_audio_video(
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        srt_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Replace original audio with new audio track and optionally burn subtitles."""
        try:
            logger.info(f"Merging {'audio and subtitles' if srt_path else 'audio'} into {video_path}")
            if srt_path and srt_path.exists():
                escaped_srt = VideoService._ffmpeg_subtitle_path(srt_path)
                filter_str = f"subtitles='{escaped_srt}':force_style='FontName=Arial,FontSize=24,BorderStyle=3,Outline=1,OutlineColour=&H80000000,Shadow=0,MarginV=20'"
                
                command = [
                    "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                    "-vf", filter_str,
                    "-af", "apad",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "192k",
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-shortest", str(output_path)
                ]
            else:
                command = [
                    "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                    "-af", "apad",
                    "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
                    "-shortest", str(output_path)
                ]
            return VideoService._run_ffmpeg_with_progress(
                command,
                duration=VideoService.get_duration(audio_path),
                progress_callback=progress_callback,
            )
        except Exception as e:
            logger.error(f"Merging error: {e}")
            return False

    @staticmethod
    def image_audio_to_video(
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        srt_path: Optional[Path] = None,
        font_size: int = 24,
        aspect_ratio: str = "16:9",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Create a motion-driven studio video from a static image and audio."""
        try:
            logger.info(f"Generating Studio video from {image_path} and {audio_path}")
            width, height = VideoService._canvas_size(aspect_ratio)
            ass_path: Optional[Path] = None
            subtitle_filter = ""
            if srt_path and srt_path.exists():
                ass_path = output_path.with_suffix(".ass")
                VideoService._create_pop_ass(srt_path, ass_path, (width, height))
                subtitle_filter = f",ass='{VideoService._ffmpeg_subtitle_path(ass_path)}'"

            motion_filter = (
                f"fps=30,"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"zoompan=z='min(zoom+0.0009,1.10)':"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"d=1:s={width}x{height}:fps=30,"
                f"eq=saturation=1.08:contrast=1.03:brightness=0.01"
                f"{subtitle_filter},format=yuv420p"
            )

            command = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(image_path),
                "-i", str(audio_path),
                "-vf", motion_filter,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-pix_fmt", "yuv420p",
                str(output_path)
            ]
            return VideoService._run_ffmpeg_with_progress(
                command,
                duration=VideoService.get_duration(audio_path),
                progress_callback=progress_callback,
            )
        except Exception as e:
            logger.error(f"Studio generation error: {e}")
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

    @staticmethod
    def create_silence(duration: float, output_path: Path, sample_rate: int = 16000) -> bool:
        """Generate a silent audio file of specific duration."""
        try:
            command = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=mono",
                "-t", str(duration), str(output_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Silence generation error: {e.stderr.decode()}")
            return False

    @staticmethod
    def separate_audio_demucs(audio_path: Path, output_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Uses Demucs to separate vocals from background music (BGM).
        Returns a tuple: (vocals_path, no_vocals_path).
        Requires 'demucs' to be installed.
        """
        try:
            # Demucs outputs to <output_dir>/htdemucs/<filename>/vocals.wav and no_vocals.wav
            logger.info(f"Running Demucs vocal separation on {audio_path}...")
            command = [
                "python", "-m", "demucs.separate",
                "-n", "htdemucs", # Fast and good model
                "--two-stems", "vocals", # Only output vocals and no_vocals
                "-o", str(output_dir),
                str(audio_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            base_name = audio_path.stem
            vocals_path = output_dir / "htdemucs" / base_name / "vocals.wav"
            bgm_path = output_dir / "htdemucs" / base_name / "no_vocals.wav"
            
            if vocals_path.exists() and bgm_path.exists():
                return vocals_path, bgm_path
            return None, None
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Demucs separation error: {e.stderr.decode() if e.stderr else str(e)}")
            return None, None
        except Exception as e:
            logger.error(f"Demucs execution failed: {e}")
            return None, None
