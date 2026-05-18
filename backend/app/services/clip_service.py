"""Plan and export vertical/social clips from completed dub jobs."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from app.core.config import settings
from app.services.video_service import VideoService
from app.utils.artifacts import resolve_artifact_paths

logger = logging.getLogger(__name__)

PlatformId = Literal["tiktok", "youtube_shorts", "instagram_reels", "custom"]
SplitMode = Literal["scene", "fixed"]

PLATFORM_PRESETS: dict[str, dict[str, Any]] = {
    "tiktok": {"max_duration": 60.0, "aspect": "9:16", "label": "TikTok"},
    "youtube_shorts": {"max_duration": 60.0, "aspect": "9:16", "label": "YouTube Shorts"},
    "instagram_reels": {"max_duration": 90.0, "aspect": "9:16", "label": "Instagram Reels"},
    "custom": {"max_duration": 60.0, "aspect": "original", "label": "Custom"},
}


@dataclass
class ClipSegment:
    start: float
    end: float
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "duration": self.end - self.start, "label": self.label}


class ClipService:
    def resolve_source_video(self, job_id: str, job: dict) -> Path:
        resolved = resolve_artifact_paths(job_id)
        output_name = job.get("output_path")
        if output_name:
            candidate = settings.OUTPUT_DIR / Path(str(output_name)).name
            if candidate.exists():
                return candidate
        source = resolved.get("source_video_path")
        if source and source.exists():
            return source
        raise FileNotFoundError("No video file found for this job.")

    @staticmethod
    def plan_clips(
        video_duration: float,
        *,
        max_duration: float = 60.0,
        mode: SplitMode = "scene",
        cues: Optional[list[dict[str, Any]]] = None,
    ) -> list[ClipSegment]:
        """Build clip segments for Shorts/TikTok export."""
        duration = max(video_duration, 0.1)
        max_dur = max(5.0, min(max_duration, duration))

        if mode == "fixed" or not cues:
            return ClipService._plan_fixed(duration, max_dur)

        parsed = sorted(
            [
                {
                    "start": float(c.get("start", c.get("startSec", 0))),
                    "end": float(c.get("end", c.get("endSec", 0))),
                }
                for c in cues
            ],
            key=lambda x: x["start"],
        )
        if not parsed:
            return ClipService._plan_fixed(duration, max_dur)

        clips: list[ClipSegment] = []
        chunk_start = parsed[0]["start"]
        chunk_end = parsed[0]["end"]

        for cue in parsed[1:]:
            prospective_end = max(chunk_end, cue["end"])
            if prospective_end - chunk_start <= max_dur:
                chunk_end = prospective_end
                continue
            clips.append(
                ClipSegment(
                    start=max(0.0, chunk_start),
                    end=min(duration, chunk_end),
                    label=f"Part {len(clips) + 1}",
                )
            )
            chunk_start = cue["start"]
            chunk_end = cue["end"]

        clips.append(
            ClipSegment(
                start=max(0.0, chunk_start),
                end=min(duration, chunk_end),
                label=f"Part {len(clips) + 1}",
            )
        )

        if len(clips) == 1 and clips[0].end - clips[0].start > max_dur:
            return ClipService._plan_fixed(duration, max_dur)

        return [c for c in clips if c.end - c.start >= 0.5]

    @staticmethod
    def _plan_fixed(duration: float, max_dur: float) -> list[ClipSegment]:
        clips: list[ClipSegment] = []
        start = 0.0
        while start < duration - 0.25:
            end = min(start + max_dur, duration)
            clips.append(ClipSegment(start=start, end=end, label=f"Part {len(clips) + 1}"))
            start = end
        return clips

    def export_clips(
        self,
        job_id: str,
        job: dict,
        segments: list[ClipSegment],
        *,
        vertical_crop: bool = False,
    ) -> list[dict[str, Any]]:
        source = self.resolve_source_video(job_id, job)
        out_dir = settings.OUTPUT_DIR / "clips" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        exported: list[dict[str, Any]] = []
        for i, seg in enumerate(segments):
            clip_duration = seg.end - seg.start
            if clip_duration < 0.5:
                continue
            safe_label = seg.label.replace(" ", "_").lower()
            out_path = out_dir / f"{job_id}_{safe_label}_{i + 1:02d}.mp4"
            ok = self._export_single_clip(
                source,
                out_path,
                seg.start,
                clip_duration,
                vertical_crop=vertical_crop,
            )
            if ok:
                exported.append(
                    {
                        "index": i + 1,
                        "label": seg.label,
                        "start": seg.start,
                        "end": seg.end,
                        "duration": clip_duration,
                        "filename": out_path.name,
                        "url": f"/storage/output/clips/{job_id}/{out_path.name}",
                    }
                )
        return exported

    @staticmethod
    def _export_single_clip(
        source: Path,
        output: Path,
        start: float,
        duration: float,
        *,
        vertical_crop: bool,
    ) -> bool:
        try:
            vf_parts: list[str] = []
            if vertical_crop:
                vf_parts.append(
                    "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                    "scale=1080:1920:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
                )
            vf = ",".join(vf_parts) if vf_parts else None

            command = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source),
                "-t",
                f"{duration:.3f}",
            ]
            if vf:
                command.extend(["-vf", vf])
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "22",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(output),
                ]
            )
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return output.exists() and output.stat().st_size > 0
        except subprocess.CalledProcessError as e:
            logger.error("Clip export failed: %s", e.stderr.decode() if e.stderr else e)
            return False
        except Exception as e:
            logger.error("Clip export error: %s", e)
            return False

    def plan_from_job(
        self,
        job_id: str,
        job: dict,
        *,
        platform: PlatformId = "tiktok",
        mode: SplitMode = "scene",
        max_duration: Optional[float] = None,
    ) -> dict[str, Any]:
        source = self.resolve_source_video(job_id, job)
        video_duration = VideoService.get_duration(source)
        preset = PLATFORM_PRESETS.get(platform, PLATFORM_PRESETS["tiktok"])
        cap = max_duration if max_duration is not None else float(preset["max_duration"])

        cues: list[dict[str, Any]] = []
        resolved = resolve_artifact_paths(job_id)
        transcript = resolved.get("transcript_path")
        if transcript and transcript.exists():
            import json

            raw = json.loads(transcript.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                cues = raw

        segments = self.plan_clips(
            video_duration,
            max_duration=cap,
            mode=mode,
            cues=cues if mode == "scene" else None,
        )
        return {
            "platform": platform,
            "preset": preset,
            "video_duration": video_duration,
            "max_duration": cap,
            "mode": mode,
            "clips": [s.to_dict() for s in segments],
        }
