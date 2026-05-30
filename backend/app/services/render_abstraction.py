"""Render Abstraction Layer — separates scene description from frame capture.

Requirement 2: Clean separation between static and animated render modes.
The video assembly pipeline consumes only frame lists without knowing which mode produced them.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class RenderMode(str, Enum):
    STATIC = "static"  # 1 PNG per scene (current behavior)
    ANIMATED = "animated"  # N frames per scene (CSS animation seeking)


@dataclass
class RenderResult:
    """Result of rendering a single scene."""
    frames: List[Path]
    duration: float  # scene duration in seconds
    render_time_ms: float  # wall-clock render time
    mode: RenderMode
    scene_index: int


@dataclass
class RenderMetrics:
    """Metrics for a complete render job."""
    total_frames: int = 0
    total_render_time_ms: float = 0.0
    scenes_rendered: int = 0
    fallback_count: int = 0  # scenes that fell back from animated to static


class SceneRenderer:
    """Unified scene renderer — routes to static or animated mode."""

    def __init__(
        self,
        mode: RenderMode = RenderMode.STATIC,
        fps: int = 30,
        max_scene_duration: float = 15.0,
        max_frames_per_scene: int = 450,
        width: int | None = None,
        height: int | None = None,
        scale: float = 1.0,
    ):
        self.mode = mode
        self.fps = min(fps, 30)  # Cap at 30 FPS
        self.max_scene_duration = max_scene_duration
        self.max_frames_per_scene = max_frames_per_scene
        self.width = width or 1080
        self.height = height or 1920
        self.scale = max(1.0, min(scale, 2.0))
        self._metrics = RenderMetrics()

    @property
    def metrics(self) -> RenderMetrics:
        return self._metrics

    def render_scene(
        self,
        html_path: Path,
        output_dir: Path,
        duration: float,
        scene_index: int = 0,
        *,
        playwright_service=None,
    ) -> RenderResult:
        """Render a scene — returns list of frame paths.

        In static mode: returns [single_png]
        In animated mode: returns [frame_000.png, frame_001.png, ...]
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()

        if self.mode == RenderMode.ANIMATED:
            result = self._render_animated(
                html_path, output_dir, duration, scene_index, playwright_service
            )
            if result and result.frames:
                self._update_metrics(result)
                return result
            # Fallback to static
            logger.warning("Animated render failed for scene %d, falling back to static.", scene_index)
            self._metrics.fallback_count += 1

        # Static mode (or fallback)
        result = self._render_static(html_path, output_dir, duration, scene_index, playwright_service)
        self._update_metrics(result)
        return result

    def _render_static(
        self,
        html_path: Path,
        output_dir: Path,
        duration: float,
        scene_index: int,
        playwright_service,
    ) -> RenderResult:
        """Capture a single PNG per scene."""
        start = time.time()
        png_path = output_dir / f"scene_{scene_index:03d}.png"

        if playwright_service:
            ok = playwright_service.render_scene_png(
                title="",
                text="",
                image_path=html_path,  # In this context, html_path IS the pre-written HTML
                output_png=png_path,
            )
            if not ok:
                png_path = Path("")  # Will be empty list
        else:
            # Direct Playwright screenshot
            ok = self._screenshot_html(html_path, png_path)

        frames = [png_path] if png_path.exists() else []
        elapsed = (time.time() - start) * 1000

        return RenderResult(
            frames=frames,
            duration=duration,
            render_time_ms=elapsed,
            mode=RenderMode.STATIC,
            scene_index=scene_index,
        )

    def _render_animated(
        self,
        html_path: Path,
        output_dir: Path,
        duration: float,
        scene_index: int,
        playwright_service,
    ) -> Optional[RenderResult]:
        """Capture N frames per scene using negative animation-delay seeking.

        For each frame, sets animation-delay to a negative value that "seeks"
        all CSS animations to the target time. This produces smooth motion
        without JavaScript — pure CSS deterministic rendering.
        """
        start = time.time()
        capped_duration = min(duration, self.max_scene_duration)
        effective_fps = max(12, min(self.fps, 30))
        n_frames = min(
            int(capped_duration * effective_fps),
            self.max_frames_per_scene,
        )

        if n_frames < 3:
            return None  # Too short for animation

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not available for animated render.")
            return None

        frames: List[Path] = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=["--disable-dev-shm-usage", "--disable-gpu"],
                )
                page = browser.new_page(
                    viewport={"width": self.width, "height": self.height},
                    device_scale_factor=self.scale,
                )
                page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=20000)
                page.wait_for_timeout(200)
                try:
                    page.wait_for_function(
                        "document.fonts ? document.fonts.status === 'loaded' : true",
                        timeout=10000,
                    )
                except Exception:
                    pass
                try:
                    page.wait_for_selector(".scene", timeout=10_000)
                except Exception:
                    pass

                # Pause all animations initially
                page.evaluate("document.getAnimations().forEach(a => a.pause())")

                for i in range(n_frames):
                    t = (i / max(n_frames - 1, 1)) * capped_duration
                    # Seek all animations to target time (in ms)
                    page.evaluate(f"""
                        document.getAnimations().forEach(a => {{
                            a.currentTime = {t * 1000:.1f};
                        }});
                    """)
                    page.wait_for_timeout(8)  # Let paint settle

                    frame_path = output_dir / f"scene_{scene_index:03d}_frame_{i:04d}.png"
                    page.locator(".scene").first.screenshot(path=str(frame_path), type="png")
                    if frame_path.exists():
                        frames.append(frame_path)

                    # Timeout check
                    elapsed_ms = (time.time() - start) * 1000
                    if elapsed_ms > 45000:  # 45s timeout per scene
                        logger.warning("Animated render timeout at frame %d/%d for scene %d", i, n_frames, scene_index)
                        break

                browser.close()

        except Exception as e:
            logger.error("Animated render failed for scene %d: %s", scene_index, e)
            return None

        if len(frames) < 3:
            return None

        elapsed = (time.time() - start) * 1000
        logger.info("Animated render: scene %d → %d frames in %.1fs", scene_index, len(frames), elapsed / 1000)
        return RenderResult(
            frames=frames,
            duration=capped_duration,
            render_time_ms=elapsed,
            mode=RenderMode.ANIMATED,
            scene_index=scene_index,
        )

        if not frames:
            return None

        elapsed = (time.time() - start) * 1000
        return RenderResult(
            frames=frames,
            duration=capped_duration,
            render_time_ms=elapsed,
            mode=RenderMode.ANIMATED,
            scene_index=scene_index,
        )

    def _screenshot_html(self, html_path: Path, output_png: Path) -> bool:
        """Simple Playwright screenshot of an HTML file."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": self.width, "height": self.height},
                    device_scale_factor=self.scale,
                )
                page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=15000)
                try:
                    page.wait_for_function(
                        "document.fonts ? document.fonts.status === 'loaded' : true",
                        timeout=10000,
                    )
                except Exception:
                    pass
                page.wait_for_timeout(800)
                page.locator(".scene").first.screenshot(path=str(output_png), type="png")
                browser.close()
            return output_png.exists()
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return False

    def _update_metrics(self, result: RenderResult) -> None:
        self._metrics.total_frames += len(result.frames)
        self._metrics.total_render_time_ms += result.render_time_ms
        self._metrics.scenes_rendered += 1
