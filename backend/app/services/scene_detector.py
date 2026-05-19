"""Scene Detector — analyze video for visual scene boundaries using PySceneDetect.

Used by Auto Shorts to cut at natural scene changes instead of fixed durations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SceneSegment:
    """A detected scene segment."""

    index: int
    start_time: float  # seconds
    end_time: float  # seconds

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class SceneDetector:
    """Detect visual scene changes in video using PySceneDetect content-aware detection."""

    def __init__(self, threshold: float = 27.0, min_scene_len: float = 2.0):
        """
        Args:
            threshold: Content detector threshold (lower = more sensitive). Default 27.0.
            min_scene_len: Minimum scene length in seconds. Default 2.0.
        """
        self.threshold = threshold
        self.min_scene_len = min_scene_len

    def is_available(self) -> bool:
        """Check if PySceneDetect is installed."""
        try:
            from scenedetect import detect, ContentDetector  # noqa: F401
            return True
        except ImportError:
            return False

    def detect_scenes(self, video_path: Path) -> List[SceneSegment]:
        """Detect scene boundaries in a video file.

        Returns list of SceneSegment with start/end times.
        Falls back to empty list if detection fails.
        """
        if not self.is_available():
            logger.warning("PySceneDetect not installed. Run: pip install scenedetect[opencv]")
            return []

        if not video_path.exists():
            logger.error("Video file not found: %s", video_path)
            return []

        try:
            from scenedetect import detect, ContentDetector

            logger.info("Detecting scenes in %s (threshold=%.1f)", video_path.name, self.threshold)

            scene_list = detect(
                str(video_path),
                ContentDetector(threshold=self.threshold, min_scene_len=self.min_scene_len),
            )

            segments: List[SceneSegment] = []
            for i, (start, end) in enumerate(scene_list):
                segments.append(SceneSegment(
                    index=i,
                    start_time=start.get_seconds(),
                    end_time=end.get_seconds(),
                ))

            logger.info("Detected %d scenes in %s", len(segments), video_path.name)
            return segments

        except Exception as e:
            logger.error("Scene detection failed: %s", e, exc_info=True)
            return []

    def smart_clip_boundaries(
        self,
        video_path: Path,
        max_part_duration: float = 60.0,
        min_part_duration: float = 15.0,
        subtitle_boundaries: Optional[List[float]] = None,
    ) -> List[float]:
        """Generate clip cut points for Auto Shorts using scene detection.

        Returns list of cut times (seconds) where the video should be split.
        Falls back to fixed-duration cuts if no scenes detected.
        """
        scenes = self.detect_scenes(video_path)

        if not scenes:
            # Fallback: fixed duration cuts
            from app.services.video_service import VideoService
            total = VideoService.get_duration(video_path)
            if total <= 0:
                return []
            cuts: List[float] = []
            t = max_part_duration
            while t < total - min_part_duration:
                cuts.append(t)
                t += max_part_duration
            return cuts

        # Build cut points from scene boundaries
        cuts: List[float] = []
        accumulated = 0.0
        last_cut = 0.0

        for scene in scenes:
            accumulated = scene.end_time - last_cut

            if accumulated >= max_part_duration:
                # This scene pushes us over max — cut at scene boundary
                cut_point = scene.start_time

                # If subtitle boundaries provided, snap to nearest subtitle end
                if subtitle_boundaries:
                    nearest = min(
                        subtitle_boundaries,
                        key=lambda t: abs(t - cut_point),
                        default=cut_point,
                    )
                    if abs(nearest - cut_point) < 3.0:
                        cut_point = nearest

                if cut_point - last_cut >= min_part_duration:
                    cuts.append(cut_point)
                    last_cut = cut_point

        return cuts
