"""Resource Semaphore — concurrency limiter for Playwright, FFmpeg, and GPU processes.

Requirement 4: Prevent resource exhaustion by limiting simultaneous heavy processes.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Configurable concurrency limits."""
    max_playwright: int = 2
    max_ffmpeg: int = 3
    max_gpu: int = 1


class ResourceSemaphore:
    """Global resource limiter — prevents OOM and CPU exhaustion."""

    def __init__(self, limits: ResourceLimits | None = None):
        self._limits = limits or ResourceLimits(
            max_playwright=getattr(settings, "MAX_CONCURRENT_PLAYWRIGHT", 2),
            max_ffmpeg=getattr(settings, "MAX_CONCURRENT_FFMPEG", 3),
            max_gpu=getattr(settings, "MAX_GPU_JOBS", 1),
        )
        # Async semaphores (for async pipeline code)
        self._async_playwright = asyncio.Semaphore(self._limits.max_playwright)
        self._async_ffmpeg = asyncio.Semaphore(self._limits.max_ffmpeg)
        self._async_gpu = asyncio.Semaphore(self._limits.max_gpu)
        # Thread semaphores (for sync worker code)
        self._sync_playwright = threading.Semaphore(self._limits.max_playwright)
        self._sync_ffmpeg = threading.Semaphore(self._limits.max_ffmpeg)
        self._sync_gpu = threading.Semaphore(self._limits.max_gpu)

    @asynccontextmanager
    async def playwright(self):
        """Acquire Playwright render slot (async)."""
        async with self._async_playwright:
            logger.debug("Playwright slot acquired.")
            yield

    @asynccontextmanager
    async def ffmpeg(self):
        """Acquire FFmpeg encode slot (async)."""
        async with self._async_ffmpeg:
            yield

    @asynccontextmanager
    async def gpu(self):
        """Acquire GPU slot (async)."""
        async with self._async_gpu:
            logger.debug("GPU slot acquired.")
            yield

    @contextmanager
    def playwright_sync(self):
        """Acquire Playwright render slot (sync/thread)."""
        self._sync_playwright.acquire()
        try:
            yield
        finally:
            self._sync_playwright.release()

    @contextmanager
    def ffmpeg_sync(self):
        """Acquire FFmpeg encode slot (sync/thread)."""
        self._sync_ffmpeg.acquire()
        try:
            yield
        finally:
            self._sync_ffmpeg.release()

    @contextmanager
    def gpu_sync(self):
        """Acquire GPU slot (sync/thread)."""
        self._sync_gpu.acquire()
        try:
            yield
        finally:
            self._sync_gpu.release()

    @property
    def limits(self) -> ResourceLimits:
        return self._limits


# Global singleton
resource_semaphore = ResourceSemaphore()
