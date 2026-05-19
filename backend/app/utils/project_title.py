"""Human-readable project titles for jobs and output files."""

from __future__ import annotations

import re

_GENERIC_SCENE = re.compile(
    r"^(hook|story|insight|close|mở đầu|kết|kết luận|cảnh\s*\d+|scene\s*\d+)$",
    re.IGNORECASE,
)


def derive_studio_title(
    *,
    project_name: str = "",
    research_topic: str = "",
    script: str = "",
) -> str:
    if (project_name or "").strip():
        return project_name.strip()[:120]
    if (research_topic or "").strip():
        return research_topic.strip()[:120]
    for line in (script or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and not stripped.upper().startswith(("[STAT:", "[DEF:")):
            inner = stripped.strip("[]").strip()
            if inner and not _GENERIC_SCENE.match(inner):
                return inner[:120]
        elif not stripped.startswith("["):
            return stripped[:120]
    return "Studio video"


def derive_dub_title(
    *,
    project_name: str = "",
    upload_filename: str = "",
    url: str = "",
) -> str:
    if (project_name or "").strip():
        return project_name.strip()[:120]
    if upload_filename:
        from pathlib import Path

        return Path(upload_filename).stem[:120] or "Dubbed video"
    if url:
        return url[:80]
    return "Dubbed video"
