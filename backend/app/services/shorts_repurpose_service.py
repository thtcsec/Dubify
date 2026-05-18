"""Long video URL/file → transcribe → dub → export Part 1, Part 2, … vertical clips."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from app.services.clip_service import ClipSegment, ClipService

logger = logging.getLogger(__name__)


def export_dubbed_shorts_parts(
    job_id: str,
    dubbed_video: Path,
    *,
    max_part_duration: float = 60.0,
    vertical_crop: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> list[dict[str, Any]]:
    """
    After full-video dubbing, split into labeled parts using transcript scene boundaries.
    """
    clip_service = ClipService()
    job_stub = {"output_path": dubbed_video.name, "id": job_id}
    plan = clip_service.plan_from_job(
        job_id,
        job_stub,
        platform="tiktok",
        mode="scene",
        max_duration=max_part_duration,
    )
    segments = [
        ClipSegment(start=float(c["start"]), end=float(c["end"]), label=str(c["label"]))
        for c in plan.get("clips", [])
    ]
    if not segments:
        segments = [
            ClipSegment(start=float(c["start"]), end=float(c["end"]), label=str(c["label"]))
            for c in ClipService.plan_clips(
                float(plan.get("video_duration") or 60),
                max_duration=max_part_duration,
                mode="fixed",
            )
        ]

    exported: list[dict[str, Any]] = []
    total = len(segments)
    for index, seg in enumerate(segments):
        if progress_callback:
            progress_callback(
                index / max(total, 1),
                f"Exporting {seg.label} ({index + 1}/{total})…",
            )
        batch = clip_service.export_clips(
            job_id,
            job_stub,
            [seg],
            vertical_crop=vertical_crop,
        )
        exported.extend(batch)

    return exported
