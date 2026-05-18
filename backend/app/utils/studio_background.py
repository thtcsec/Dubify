"""Default studio background when user does not upload an image."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.studio_html_service import ASPECT_TO_SIZE
from app.services.video_service import VideoService


def ensure_studio_background(
    job_id: str,
    aspect_ratio: str = "9:16",
    *,
    image_path: Optional[str | Path] = None,
) -> Path:
    """Return user image if present, otherwise generate a gradient placeholder."""
    if image_path:
        path = Path(image_path)
        if path.exists() and path.stat().st_size > 0:
            width, height = ASPECT_TO_SIZE.get(aspect_ratio, (1080, 1920))
            fitted = settings.TEMP_DIR / f"{job_id}_studio_bg_{width}x{height}.png"
            if not fitted.exists() or fitted.stat().st_size == 0:
                VideoService.fit_image_cover(path, fitted, width, height)
            return fitted

    width, height = ASPECT_TO_SIZE.get(aspect_ratio, (1080, 1920))
    out = settings.TEMP_DIR / f"{job_id}_studio_gradient.png"
    if not out.exists() or out.stat().st_size == 0:
        VideoService.create_gradient_background(
            out,
            width,
            height,
            top_color="#0c1222",
            bottom_color="#1d4ed8",
        )
    return out
