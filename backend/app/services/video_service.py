import subprocess
import os
import shutil
import logging
import tempfile
import re
import threading
from pathlib import Path
from typing import Optional, Tuple, Callable
import numpy as np
from PIL import Image
from app.core.config import settings
from app.core.gpu import video_encoder_args
from app.utils.subtitles import wrap_subtitle_text

logger = logging.getLogger(__name__)

# Pixelle-style scene transitions (FFmpeg xfade)
STUDIO_XFADE_TRANSITIONS = (
    "fade",
    "smoothleft",
    "smoothright",
    "slideup",
    "slideright",
    "fadeblack",
    "wiperight",
    "wipeleft",
    "dissolve",
    "zoomin",
    "slideleft",
    "fadewhite",
)

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
        return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))

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
    def fit_image_cover(source: Path, output: Path, width: int, height: int) -> Path:
        """Cover-crop image to exact canvas (fixes wrong aspect when switching 9:16 ↔ 16:9)."""
        from PIL import Image as PILImage

        img = PILImage.open(source).convert("RGB")
        src_w, src_h = img.size
        scale = max(width / src_w, height / src_h)
        resized = img.resize((int(src_w * scale), int(src_h * scale)), PILImage.Resampling.LANCZOS)
        left = (resized.width - width) // 2
        top = (resized.height - height) // 2
        cropped = resized.crop((left, top, left + width, top + height))
        output.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output, "PNG")
        return output

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
    def get_video_size(file_path: Path) -> Tuple[int, int]:
        """Return (width, height) of the first video stream."""
        try:
            command = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0:s=x",
                str(file_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            w_str, h_str = result.stdout.strip().split("x")
            return max(int(w_str), 1), max(int(h_str), 1)
        except Exception as e:
            logger.warning("Could not read video size for %s: %s", file_path, e)
            return VideoService.ASPECT_RATIOS["16:9"]

    @staticmethod
    def _subtitle_style_for_height(height: int, scale: float = 1.0) -> Tuple[int, int]:
        """Font size and bottom margin scaled to output resolution."""
        font_size = max(18, min(40, int(height * 0.038 * scale)))
        margin_v = max(36, int(height * 0.07 * scale))
        return font_size, margin_v

    @staticmethod
    def _parse_media_timestamp(value: str) -> float:
        """Parse SRT/VTT timestamps (supports comma or dot ms, with or without hours)."""
        cleaned = value.strip().replace(",", ".")
        parts = cleaned.split(":")
        if len(parts) == 3:
            hh, mm, sec_part = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            hh, mm, sec_part = "0", parts[0], parts[1]
        else:
            raise ValueError(f"Invalid timestamp: {value!r}")

        if "." in sec_part:
            ss_str, ms_str = sec_part.split(".", 1)
        else:
            ss_str, ms_str = sec_part, "0"

        ms_val = int(ms_str.ljust(3, "0")[:3])
        return int(hh) * 3600 + int(mm) * 60 + int(ss_str) + ms_val / 1000.0

    @staticmethod
    def _parse_srt(srt_path: Path) -> list[tuple[float, float, str]]:
        cues: list[tuple[float, float, str]] = []
        content = srt_path.read_text(encoding="utf-8", errors="ignore")
        blocks = re.split(r"\r?\n\r?\n", content.strip())

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:
                continue
            time_line_index = 1 if re.fullmatch(r"\d+", lines[0]) else 0
            if time_line_index >= len(lines) or "-->" not in lines[time_line_index]:
                continue
            time_parts = lines[time_line_index].split("-->")
            if len(time_parts) < 2:
                continue
            start_str = time_parts[0].strip().split(" ")[0]
            end_str = time_parts[1].strip().split(" ")[0]
            text = "\n".join(lines[time_line_index + 1 :]).strip()
            if text:
                cues.append(
                    (
                        VideoService._parse_media_timestamp(start_str),
                        VideoService._parse_media_timestamp(end_str),
                        text,
                    )
                )
        return cues

    @staticmethod
    def _create_burn_ass(
        cues: list[tuple[float, float, str]],
        output_path: Path,
        canvas_size: Tuple[int, int],
        font_scale: float = 1.0,
    ) -> Path:
        """ASS subtitles with PlayRes matching video — avoids giant SRT burn scaling."""
        width, height = canvas_size
        font_size, margin_v = VideoService._subtitle_style_for_height(height, scale=font_scale)
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
            f"Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,48,48,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        for start, end, text in cues:
            wrapped = wrap_subtitle_text(text.replace("\n", " "))
            lines.append(
                f"Dialogue: 0,{VideoService._format_ass_time(start)},{VideoService._format_ass_time(end)},Default,,0,0,0,,{VideoService._escape_ass_text(wrapped)}"
            )
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    @staticmethod
    def _karaoke_layout_y_base(
        width: int,
        height: int,
        caption_y_pct: float | None = None,
    ) -> int:
        """TikTok safe zone: ~62–68% from top on vertical, lower third on landscape."""
        if caption_y_pct is not None:
            return int(height * max(35.0, min(caption_y_pct, 85.0)) / 100.0)
        if height > width:
            return int(height * 0.64)
        return int(height * 0.78)

    @staticmethod
    def _create_karaoke_ass(
        cues: list[tuple[float, float, str]],
        output_path: Path,
        canvas_size: Tuple[int, int],
        font_scale: float = 1.0,
        caption_y_pct: float | None = None,
    ) -> Path:
        """TikTok pill-karaoke: per-word highlight + mid-frame placement (HyperFrames caption-pill inspired)."""
        from app.utils.studio_karaoke import expand_cues_to_words, group_words_into_lines

        width, height = canvas_size
        portrait = height > width
        font_size = max(22, min(52, int(height * (0.042 if portrait else 0.034) * font_scale)))
        word_cues = expand_cues_to_words(cues)
        max_words = 5 if portrait else 8
        lines_grouped = group_words_into_lines(word_cues, max_words=max_words)

        inactive = "&H00B8B8B8"
        active = "&H0000FFFF"
        spoken = "&H00FFFFFF"
        y_base = VideoService._karaoke_layout_y_base(width, height, caption_y_pct)

        ass_lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            f"Style: Karaoke,Arial,{font_size},&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,3,4,0,2,48,48,80,1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]

        for _line_idx, line_words in enumerate(lines_grouped):
            if not line_words:
                continue
            # Fixed caption band — do not stack lines lower over time
            line_y = y_base
            for active_index, (w_start, w_end, _word) in enumerate(line_words):
                parts: list[str] = []
                for j, (_, __, w) in enumerate(line_words):
                    if j == active_index:
                        colour = active
                    elif j < active_index:
                        colour = spoken
                    else:
                        colour = inactive
                    safe = VideoService._escape_ass_text(w)
                    parts.append(f"{{\\1c{colour}&\\b1}}{safe}")
                line_text = " ".join(parts)
                box = "{\\3c&H50000000&\\4c&H50000000&\\bord14\\shad0}"
                pos = f"{{\\an2\\pos({width // 2},{line_y})}}"
                fade = "{\\fad(80,120)}" if active_index == 0 and _line_idx == 0 else ""
                ass_lines.append(
                    f"Dialogue: 0,{VideoService._format_ass_time(w_start)},"
                    f"{VideoService._format_ass_time(w_end)},Karaoke,,0,0,0,,"
                    f"{pos}{box}{fade}{line_text}"
                )

        output_path.write_text("\n".join(ass_lines), encoding="utf-8")
        return output_path

    @staticmethod
    def _append_popup_overlay_dialogues(
        ass_path: Path,
        popup_timings: list[tuple[float, float, dict[str, str]]],
        canvas_size: Tuple[int, int],
        caption_y_pct: float | None = None,
    ) -> None:
        """Burn [STAT]/[DEF] popup cards into an existing ASS file."""
        if not popup_timings or not ass_path.exists():
            return

        width, height = canvas_size
        portrait = height > width
        font_size = max(24, min(48, int(height * (0.038 if portrait else 0.032))))
        y_pct = caption_y_pct if caption_y_pct is not None else (62.0 if portrait else 72.0)
        popup_y = int(height * max(28.0, min(y_pct - 22.0, 52.0)) / 100.0)

        body = ass_path.read_text(encoding="utf-8")
        if "Style: StatPop" not in body:
            style_line = (
                f"Style: StatPop,Arial,{font_size},&H00B8FFFF,&H0000FFFF,&H00101010,&H90000000,"
                f"-1,0,0,0,100,100,0,0,3,3,0,2,48,48,80,1"
            )
            def_style = (
                f"Style: DefPop,Arial,{max(18, font_size - 2)},&H00E8B8FF,&H00E8B8FF,&H00101010,&H90000000,"
                f"-1,0,0,0,100,100,0,0,3,3,0,2,48,48,80,1"
            )
            body = body.replace("[Events]", f"{style_line}\n{def_style}\n\n[Events]", 1)

        lines = body.splitlines()
        for start, end, popup in popup_timings:
            label = "STAT" if popup.get("type") == "stat" else "DEF"
            style = "StatPop" if popup.get("type") == "stat" else "DefPop"
            text = VideoService._escape_ass_text(str(popup.get("text") or ""))
            if not text:
                continue
            # Enhanced animation: scale bounce + blur fade for more visual impact
            box = r"{\3c&H40000000&\4c&H60000000&\bord18\shad0}"
            anim = r"{\fad(150,250)\fscx80\fscy80\t(0,350,\fscx115\fscy115)\t(350,500,\fscx100\fscy100)\blur0.6\t(0,200,\blur0)}"
            pos = f"{{\\an8\\pos({width // 2},{popup_y})}}"
            lines.append(
                f"Dialogue: 2,{VideoService._format_ass_time(start)},{VideoService._format_ass_time(end)},"
                f"{style},,0,0,0,,{pos}{box}{anim}{label}: {text}"
            )
        ass_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _parse_vtt(vtt_path: Path) -> list[tuple[float, float, str]]:
        cues: list[tuple[float, float, str]] = []
        content = vtt_path.read_text(encoding="utf-8", errors="ignore")
        blocks = re.split(r"\r?\n\r?\n", content.strip())

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines or lines[0].upper() == "WEBVTT":
                continue
            time_line_index = 0 if "-->" in lines[0] else 1
            if time_line_index >= len(lines) or "-->" not in lines[time_line_index]:
                continue
            time_parts = lines[time_line_index].split("-->")
            if len(time_parts) < 2:
                continue
            start_str = time_parts[0].strip().split(" ")[0]
            end_str = time_parts[1].strip().split(" ")[0]
            text = " ".join(lines[time_line_index + 1 :]).strip()
            if text:
                cues.append(
                    (
                        VideoService._parse_media_timestamp(start_str),
                        VideoService._parse_media_timestamp(end_str),
                        text,
                    )
                )
        return cues

    @staticmethod
    def _create_pop_ass(vtt_path: Path, output_path: Path, canvas_size: Tuple[int, int]) -> Path:
        width, height = canvas_size
        font_size, margin_v = VideoService._subtitle_style_for_height(height)
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
            f"Style: Pop,Arial,{font_size},&H00FFFFFF,&H0000F0FF,&H00111111,&H66000000,-1,0,0,0,100,100,0,0,1,2,0,2,64,64,{margin_v},1",
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
    def _grain_vignette_filter() -> str:
        """Build FFmpeg filter string for grain and vignette based on settings."""
        parts = []
        if getattr(settings, "STUDIO_GRAIN_ENABLED", True):
            seed = getattr(settings, "STUDIO_GRAIN_SEED", 42)
            parts.append(f"noise=c0s=3:c0f=t:c0_seed={seed}")
        if getattr(settings, "STUDIO_VIGNETTE_ENABLED", True):
            parts.append("vignette=PI/5")
        if parts:
            return "," + ",".join(parts)
        return ""

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
    def _drain_stderr(stderr) -> None:
        """Prevent FFmpeg from blocking when the stderr pipe buffer fills."""
        if stderr is None:
            return
        try:
            for _ in stderr:
                pass
        except Exception:
            pass

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
        stderr_thread = threading.Thread(
            target=VideoService._drain_stderr,
            args=(process.stderr,),
            daemon=True,
        )
        stderr_thread.start()
        last_ratio = 0.0
        last_log_pct = -1
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
                    pct = int(ratio * 100)
                    if pct >= last_log_pct + 10:
                        last_log_pct = pct
                        logger.info("FFmpeg encode progress: %s%%", pct)
            stderr_thread.join(timeout=2)
            if process.wait() != 0:
                logger.error("FFmpeg exited with code %s", process.returncode)
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
        """Stretch or compress audio to match target duration using FFmpeg."""
        try:
            current_duration = VideoService.get_duration(input_file)
            if current_duration <= 0 or target_duration <= 0:
                return False

            ratio = current_duration / target_duration

            if abs(ratio - 1.0) < 0.03:
                shutil.copyfile(input_file, output_file)
                return True

            # Large mismatch: trim or pad instead of extreme time-stretch (sounds more natural).
            if ratio > 1.28:
                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(input_file),
                    "-af",
                    f"atrim=0:{target_duration:.3f},asetpts=PTS-STARTPTS",
                    str(output_file),
                ]
                subprocess.run(
                    command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                return output_file.exists() and output_file.stat().st_size > 0

            if ratio < 0.78:
                pad = max(0.0, target_duration - current_duration)
                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(input_file),
                    "-af",
                    f"apad=pad_dur={pad:.3f}",
                    str(output_file),
                ]
                subprocess.run(
                    command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                return output_file.exists() and output_file.stat().st_size > 0

            # Mild stretch: rubberband first, then atempo chain.
            filter_str = f"rubberband=tempo={ratio:.4f}"
            command = [
                "ffmpeg", "-y", "-i", str(input_file),
                "-filter:a", filter_str,
                str(output_file)
            ]
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if result.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0:
                return True

            # Fallback: atempo filter (supports 0.5-100.0, chain for extreme values)
            logger.info("Rubberband unavailable, falling back to atempo filter.")
            atempo_filters = []
            r = ratio
            # atempo only supports 0.5 to 100.0 per filter, chain for values outside range
            while r > 2.0:
                atempo_filters.append("atempo=2.0")
                r /= 2.0
            while r < 0.5:
                atempo_filters.append("atempo=0.5")
                r /= 0.5
            atempo_filters.append(f"atempo={r:.4f}")
            filter_str = ",".join(atempo_filters)

            command = [
                "ffmpeg", "-y", "-i", str(input_file),
                "-filter:a", filter_str,
                str(output_file)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return output_file.exists() and output_file.stat().st_size > 0
        except subprocess.CalledProcessError as e:
            logger.error(f"Audio stretch error: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Audio stretch error: {e}")
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
                width, height = VideoService.get_video_size(video_path)
                ass_path = srt_path.with_suffix(".burn.ass")
                cues = VideoService._parse_srt(srt_path)
                if not cues:
                    cues = VideoService._parse_vtt(srt_path)
                VideoService._create_burn_ass(cues, ass_path, (width, height))
                escaped_ass = VideoService._ffmpeg_subtitle_path(ass_path)
                filter_str = f"ass='{escaped_ass}'"

                command = [
                    "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                    "-vf", filter_str,
                    "-af", "apad",
                    *video_encoder_args(crf=23),
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
            video_duration = VideoService.get_duration(video_path)
            audio_duration = VideoService.get_duration(audio_path)
            duration = max(video_duration, audio_duration, 1.0)
            logger.info(
                "Merge encode started (video %.1fs, audio %.1fs) — may take several minutes with burned subtitles",
                video_duration,
                audio_duration,
            )
            return VideoService._run_ffmpeg_with_progress(
                command,
                duration=duration,
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
                cues = (
                    VideoService._parse_srt(srt_path)
                    if srt_path.suffix.lower() == ".srt"
                    else VideoService._parse_vtt(srt_path)
                )
                VideoService._create_karaoke_ass(cues, ass_path, (width, height), font_scale=1.25)
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
                f"{VideoService._grain_vignette_filter()}"
                f"{subtitle_filter}"
                f",format=yuv420p"
            )

            command = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(image_path),
                "-i", str(audio_path),
                "-vf", motion_filter,
                *video_encoder_args(crf=23),
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
    def frames_to_video_segment(
        frame_paths: list,
        output_path: Path,
        duration: float,
        fps: int = 12,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        """Assemble a sequence of PNG frames into a video segment.

        Used for animated scene rendering (multi-frame per scene).
        """
        if not frame_paths:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create frame list file for FFmpeg
        list_file = output_path.with_suffix(".frames.txt")
        frame_duration = duration / len(frame_paths)
        with open(list_file, "w", encoding="utf-8") as f:
            for frame_path in frame_paths:
                f.write(f"file '{Path(frame_path).resolve().as_posix()}'\n")
                f.write(f"duration {frame_duration:.4f}\n")
            # Last frame needs to be listed again (FFmpeg concat demuxer quirk)
            f.write(f"file '{Path(frame_paths[-1]).resolve().as_posix()}'\n")

        try:
            command = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-r", str(fps),
                *video_encoder_args(crf=20),
                "-an",
                str(output_path),
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            list_file.unlink(missing_ok=True)
            return output_path.exists() and output_path.stat().st_size > 0
        except Exception as e:
            logger.error("Frame sequence assembly failed: %s", e)
            list_file.unlink(missing_ok=True)
            return False

    @staticmethod
    def _scene_motion_filter(width: int, height: int, duration: float, scene_index: int) -> str:
        """Ken Burns / pan on each scene PNG so HTML cards are not frozen stills."""
        frames = max(int(duration * 30), 90)
        scale_crop = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
        )
        mode = scene_index % 4
        if mode == 0:
            z = (
                f"zoompan=z='min(1+0.00042*on,1.12)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            )
        elif mode == 1:
            z = (
                f"zoompan=z='max(1.12-0.00042*on,1.02)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            )
        elif mode == 2:
            z = (
                f"zoompan=z='1.08':"
                f"x='max(0,(iw-iw/zoom)*(on/{frames}))':y='ih/2-(ih/zoom/2)'"
            )
        else:
            z = (
                f"zoompan=z='1.08':"
                f"x='max(0,(iw-iw/zoom)*(1-on/{frames}))':y='ih/2-(ih/zoom/2)'"
            )
        return f"{scale_crop}{z}:d={frames}:s={width}x{height}:fps=30,format=yuv420p"

    @staticmethod
    def studio_scenes_to_video(
        scene_pngs: list[tuple[Path, float]],
        audio_path: Path,
        output_path: Path,
        srt_path: Optional[Path] = None,
        aspect_ratio: str = "9:16",
        progress_callback: Optional[Callable[[float], None]] = None,
        fade_seconds: float = 0.45,
        karaoke_subs: bool = False,
        burn_subtitles: bool = False,
        caption_y_pct: float | None = None,
        popup_timings: list[tuple[float, float, dict[str, str]]] | None = None,
    ) -> bool:
        """Assemble HTML scene slides with Ken Burns motion + crossfades."""
        if not scene_pngs:
            return False

        try:
            width, height = VideoService._canvas_size(aspect_ratio)
            temp_dir = settings.TEMP_DIR / f"studio_scenes_{output_path.stem}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            segment_paths: list[Path] = []

            fade = max(0.35, min(fade_seconds, 0.85))
            for index, (png_path, duration) in enumerate(scene_pngs):
                seg_out = temp_dir / f"scene_{index:03d}.mp4"
                dur = max(duration, fade + 0.5)  # Ensure scene > fade duration
                if len(scene_pngs) > 1:
                    dur += fade * 0.5

                # Check if this is a frame sequence directory (animated render)
                frame_dir = png_path.parent / f"scene_{index:03d}_frames"
                if frame_dir.exists() and frame_dir.is_dir():
                    frame_files = sorted(frame_dir.glob("*.png"))
                    if len(frame_files) >= 3:
                        # Use frame sequence (animated render — smooth motion)
                        if VideoService.frames_to_video_segment(
                            frame_files, seg_out, dur, fps=12, width=width, height=height
                        ):
                            segment_paths.append(seg_out)
                            continue

                # Fallback: single PNG with Ken Burns motion
                motion_filter = VideoService._scene_motion_filter(width, height, dur, index)
                command = [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(png_path),
                    "-t",
                    f"{dur:.3f}",
                    "-vf",
                    motion_filter,
                    *video_encoder_args(crf=22),
                    "-an",
                    str(seg_out),
                ]
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if seg_out.exists():
                    segment_paths.append(seg_out)

            if not segment_paths:
                return False

            if len(segment_paths) == 1:
                video_only = segment_paths[0]
            else:
                video_only = temp_dir / "xfade_merged.mp4"
                transitions = [
                    STUDIO_XFADE_TRANSITIONS[i % len(STUDIO_XFADE_TRANSITIONS)]
                    for i in range(len(segment_paths) - 1)
                ]
                VideoService._xfade_chain(
                    segment_paths, video_only, fade_seconds=fade, transitions=transitions
                )

            audio_duration = max(VideoService.get_duration(audio_path), 0.1)
            video_duration = VideoService.get_duration(video_only)
            vf_parts: list[str] = []
            if video_duration + 0.05 < audio_duration:
                pad = audio_duration - video_duration
                vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad:.3f}")

            if burn_subtitles and srt_path and srt_path.exists():
                ass_path = output_path.with_suffix(".ass")
                cues = (
                    VideoService._parse_srt(srt_path)
                    if srt_path.suffix.lower() == ".srt"
                    else VideoService._parse_vtt(srt_path)
                )
                if karaoke_subs:
                    VideoService._create_karaoke_ass(
                        cues,
                        ass_path,
                        (width, height),
                        font_scale=1.35,
                        caption_y_pct=caption_y_pct,
                    )
                else:
                    VideoService._create_burn_ass(cues, ass_path, (width, height), font_scale=1.45)
                if popup_timings:
                    VideoService._append_popup_overlay_dialogues(
                        ass_path,
                        popup_timings,
                        (width, height),
                        caption_y_pct=caption_y_pct,
                    )
                vf_parts.append(f"ass='{VideoService._ffmpeg_subtitle_path(ass_path)}'")

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_only),
                "-i",
                str(audio_path),
            ]
            if vf_parts:
                command.extend(["-vf", ",".join(vf_parts), *video_encoder_args(crf=20)])
            else:
                command.extend(["-c:v", "copy"])
            command.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-t",
                    f"{audio_duration:.3f}",
                    str(output_path),
                ]
            )
            return VideoService._run_ffmpeg_with_progress(
                command,
                duration=VideoService.get_duration(audio_path),
                progress_callback=progress_callback,
            )
        except Exception as e:
            logger.error("Studio HTML scene assembly failed: %s", e)
            return False

    @staticmethod
    def _xfade_chain(
        segment_paths: list[Path],
        output_path: Path,
        fade_seconds: float,
        transitions: Optional[list[str]] = None,
    ) -> None:
        """Chain xfade transitions across scene segments (Pixelle-style cuts)."""
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output_path)
            return

        current = segment_paths[0]
        fade = max(0.35, min(fade_seconds, 1.0))
        transition_list = transitions or ["fade"] * (len(segment_paths) - 1)
        for index, nxt in enumerate(segment_paths[1:], start=1):
            merged = output_path.parent / f"xfade_{index}.mp4"
            dur_current = VideoService.get_duration(current)
            dur_next = VideoService.get_duration(nxt)

            # Skip xfade if either segment is too short — just concat instead
            if dur_current < fade + 0.5 or dur_next < fade + 0.5:
                logger.warning("Scene %d too short for xfade (%.1fs), using hard cut.", index, min(dur_current, dur_next))
                # Simple concat without transition
                list_file = output_path.parent / f"concat_{index}.txt"
                list_file.write_text(
                    f"file '{Path(current).resolve().as_posix()}'\nfile '{Path(nxt).resolve().as_posix()}'\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(merged)],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
                list_file.unlink(missing_ok=True)
                current = merged
                continue

            offset = max(dur_current - fade, 0.2)
            transition = transition_list[index - 1] if index - 1 < len(transition_list) else "fade"
            if transition not in STUDIO_XFADE_TRANSITIONS:
                transition = "fade"
            filter_complex = (
                f"[0:v][1:v]xfade=transition={transition}:duration={fade:.3f}:offset={offset:.3f}[v]"
            )
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(current),
                        "-i", str(nxt),
                        "-filter_complex", filter_complex,
                        "-map", "[v]",
                        *video_encoder_args(crf=22),
                        str(merged),
                    ],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError:
                # NVENC can fail on short segments — retry with CPU encoder
                logger.warning("xfade with HW encoder failed at scene %d, retrying with libx264.", index)
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(current),
                        "-i", str(nxt),
                        "-filter_complex", filter_complex,
                        "-map", "[v]",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        str(merged),
                    ],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                )
            current = merged
        shutil.copy2(current, output_path)

    @staticmethod
    def apply_studio_branding(
        video_path: Path,
        output_path: Path,
        aspect_ratio: str,
        branding,
        layout=None,
    ) -> bool:
        """Composite optional header/footer text or logo strips onto finished video."""
        from app.utils.studio_overlay import StudioLayout, branding_active, render_branding_png

        if not branding_active(branding):
            shutil.copy2(video_path, output_path)
            return True

        layout = layout or StudioLayout()
        width, height = VideoService._canvas_size(aspect_ratio)
        band_h = max(int(height * 0.11), 88)
        temp_dir = settings.TEMP_DIR / f"brand_{video_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        inputs = ["-i", str(video_path)]
        filter_parts: list[str] = []
        stream_label = "0:v"
        input_index = 1

        if branding.header.enabled:
            header_png = temp_dir / "header.png"
            render_branding_png(
                width=width,
                height=band_h,
                band=branding.header,
                band_height=band_h,
                position="header",
            ).save(header_png)
            inputs.extend(["-i", str(header_png)])
            out_label = f"v{input_index}"
            header_y = max(0, min(int(height * layout.header_y_pct / 100.0), height - band_h))
            filter_parts.append(
                f"[{stream_label}][{input_index}:v]overlay=0:{header_y}:format=auto[{out_label}]"
            )
            stream_label = out_label
            input_index += 1

        if branding.footer.enabled:
            footer_png = temp_dir / "footer.png"
            render_branding_png(
                width=width,
                height=band_h,
                band=branding.footer,
                band_height=band_h,
                position="footer",
            ).save(footer_png)
            inputs.extend(["-i", str(footer_png)])
            y = max(0, min(int(height * layout.footer_y_pct / 100.0), height - band_h))
            out_label = f"v{input_index}"
            filter_parts.append(
                f"[{stream_label}][{input_index}:v]overlay=0:{y}:format=auto[{out_label}]"
            )
            stream_label = out_label
            input_index += 1

        if not filter_parts:
            shutil.copy2(video_path, output_path)
            return True

        filter_complex = ";".join(filter_parts)
        command = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{stream_label}]",
            "-map",
            "0:a?",
            *video_encoder_args(crf=20),
            "-c:a",
            "copy",
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return output_path.exists()
        except subprocess.CalledProcessError as exc:
            logger.error("Studio branding overlay failed: %s", exc.stderr.decode(errors="replace")[:500])
            shutil.copy2(video_path, output_path)
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
