"""Remove on-disk files tied to a dubbing job."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.utils.artifacts import remove_job_artifacts


def _unlink(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)
    except OSError:
        pass


def remove_job_storage(job_id: str, job: Optional[dict[str, Any]] = None) -> None:
    """Delete artifacts, temp sessions, clips, inputs, and rendered output for one job."""
    remove_job_artifacts(job_id)

    temp_root = settings.TEMP_DIR
    session = temp_root / job_id
    _unlink(session)
    for path in temp_root.glob(f"{job_id}*"):
        _unlink(path)

    clips_dir = settings.OUTPUT_DIR / "clips" / job_id
    _unlink(clips_dir)

    for folder in (settings.INPUT_DIR, settings.OUTPUT_DIR):
        if not folder.exists():
            continue
        for path in folder.glob(f"{job_id}*"):
            if path.is_dir() and path.name == "clips":
                continue
            _unlink(path)

    output_path: Optional[Path] = None
    if job:
        raw = job.get("output_path")
        if raw:
            candidate = Path(str(raw))
            output_path = candidate if candidate.is_absolute() else settings.OUTPUT_DIR / candidate.name

    if output_path and output_path.exists():
        _unlink(output_path)
    else:
        for path in settings.OUTPUT_DIR.glob(f"*{job_id}*"):
            if path.is_dir() and path.name == "clips":
                continue
            _unlink(path)
