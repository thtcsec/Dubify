"""Persist dubbing artifacts outside ephemeral temp sessions."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings

_ARTIFACT_FILES = ("transcript.json", "translated.srt", "dubbed_audio.wav")


def artifact_dir(job_id: str) -> Path:
    return settings.ARTIFACTS_DIR / job_id


def persist_dubbing_artifacts(
    job_id: str,
    session_dir: Path,
    *,
    source_video: Optional[Path] = None,
) -> Optional[Path]:
    """Copy subtitle/transcript/audio (and optional source video) into durable storage."""
    if not session_dir.exists() and not source_video:
        return None

    dest = artifact_dir(job_id)
    dest.mkdir(parents=True, exist_ok=True)
    copied = False
    for name in _ARTIFACT_FILES:
        src = session_dir / name
        if name == "dubbed_audio.wav":
            alt = session_dir / "dubbed_audio_final.wav"
            if not src.exists() and alt.exists():
                src = alt
        if src.exists() and src.stat().st_size > 0:
            shutil.copy2(src, dest / name)
            copied = True
    if source_video and source_video.exists():
        ext = source_video.suffix or ".mp4"
        shutil.copy2(source_video, dest / f"source_video{ext}")
        copied = True
    return dest if copied else None


def resolve_artifact_paths(job_id: str) -> dict[str, Optional[Path]]:
    """Locate artifact files (durable store first, then temp session)."""
    result: dict[str, Optional[Path]] = {
        "transcript_path": None,
        "subtitle_path": None,
        "audio_path": None,
        "source_video_path": None,
        "session_dir": None,
    }

    durable = artifact_dir(job_id)
    if durable.exists():
        transcript = durable / "transcript.json"
        subtitle = durable / "translated.srt"
        audio = durable / "dubbed_audio.wav"
        source_candidates = list(durable.glob("source_video.*"))
        if transcript.exists():
            result["transcript_path"] = transcript
        if subtitle.exists():
            result["subtitle_path"] = subtitle
        if audio.exists():
            result["audio_path"] = audio
        if source_candidates:
            result["source_video_path"] = source_candidates[0]
        if any(result[k] for k in ("transcript_path", "subtitle_path", "audio_path", "source_video_path")):
            result["session_dir"] = durable
            return result

    session_dir = settings.TEMP_DIR / job_id
    if session_dir.exists():
        result["session_dir"] = session_dir
        transcript = session_dir / "transcript.json"
        subtitle = session_dir / "translated.srt"
        if transcript.exists():
            result["transcript_path"] = transcript
        if subtitle.exists():
            result["subtitle_path"] = subtitle

    studio_subtitle = settings.TEMP_DIR / f"{job_id}_tts.vtt"
    if studio_subtitle.exists() and not result["subtitle_path"]:
        result["subtitle_path"] = studio_subtitle

    return result


def remove_job_artifacts(job_id: str) -> None:
    shutil.rmtree(artifact_dir(job_id), ignore_errors=True)
