"""Re-render dubbed videos from edited subtitle tracks."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.video_service import VideoService
from app.utils.artifacts import artifact_dir, resolve_artifact_paths

logger = logging.getLogger(__name__)


class EditorService:
    def __init__(self) -> None:
        self.video_service = VideoService()

    def burn_subtitles(
        self,
        job_id: str,
        srt_content: str,
        *,
        output_suffix: str = "_edited",
    ) -> Path:
        resolved = resolve_artifact_paths(job_id)
        source_video = resolved.get("source_video_path")
        dubbed_audio = resolved.get("audio_path")

        if not source_video or not source_video.exists():
            raise FileNotFoundError(
                "Source video not found in artifacts. Re-run dubbing after updating the app "
                "so source_video is persisted for the editor."
            )
        if not dubbed_audio or not dubbed_audio.exists():
            raise FileNotFoundError("Dubbed audio track not found in artifacts.")

        dest = artifact_dir(job_id)
        dest.mkdir(parents=True, exist_ok=True)
        srt_path = dest / "edited.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        out_name = f"{job_id}{output_suffix}_{source_video.name}"
        output_path = settings.OUTPUT_DIR / out_name

        ok = self.video_service.merge_audio_video(
            source_video,
            dubbed_audio,
            output_path,
            srt_path,
        )
        if not ok:
            raise RuntimeError("FFmpeg failed to burn subtitles into video.")

        shutil.copy2(srt_path, dest / "translated.srt")
        logger.info("Editor burn complete: %s", output_path)
        return output_path
