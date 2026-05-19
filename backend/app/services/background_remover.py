"""Background Removal — remove backgrounds from images using rembg.

Requirement 19: Composite subjects onto custom scene backgrounds.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BackgroundRemover:
    """Remove backgrounds from images using rembg."""

    def __init__(self):
        self._model_loaded = False

    def is_available(self) -> bool:
        """Check if rembg is installed."""
        try:
            import rembg  # noqa: F401
            return True
        except ImportError:
            return False

    def remove_background(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Remove background from an image.

        Args:
            input_path: Source image (PNG, JPEG, WebP)
            output_path: Output PNG path (default: input_stem + _nobg.png)

        Returns:
            Path to output PNG with transparent background, or None on failure.
        """
        if not self.is_available():
            logger.warning("rembg not installed. Run: pip install rembg[gpu]")
            return None

        if not input_path.exists():
            logger.error("Input image not found: %s", input_path)
            return None

        if output_path is None:
            output_path = input_path.with_name(f"{input_path.stem}_nobg.png")

        try:
            from rembg import remove
            from PIL import Image

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load and process
            input_image = Image.open(input_path)
            output_image = remove(input_image)

            # Save as PNG (preserves transparency)
            output_image.save(output_path, "PNG")

            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info("Background removed: %s → %s", input_path.name, output_path.name)
                return output_path
            return None

        except Exception as e:
            logger.error("Background removal failed: %s", e)
            return None

    def remove_background_cached(
        self,
        input_path: Path,
        cache_dir: Path,
    ) -> Optional[Path]:
        """Remove background with caching based on file hash."""
        if not input_path.exists():
            return None

        # Generate cache key from file content
        file_hash = hashlib.md5(input_path.read_bytes()).hexdigest()[:12]
        cached_path = cache_dir / f"nobg_{file_hash}.png"

        if cached_path.exists():
            logger.debug("Background removal cache hit: %s", cached_path.name)
            return cached_path

        return self.remove_background(input_path, cached_path)
