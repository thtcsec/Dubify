"""Progress/cancel hooks for the dubbing pipeline (kept separate from orchestration)."""

from __future__ import annotations

from typing import Callable, Optional, Protocol


class DubbingReporter(Protocol):
    def check_cancel(self) -> None: ...
    def check_pause(self) -> None: ...
    def stage(self, message: str, progress: float) -> None: ...
    def translate_progress(self, done: int, total: int) -> None: ...
    def tts_progress(self, done: int, total: int) -> None: ...
    def merge_progress(self, ratio: float) -> None: ...


class NullDubbingReporter:
    def check_cancel(self) -> None:
        return

    def check_pause(self) -> None:
        return

    def stage(self, message: str, progress: float) -> None:
        return

    def translate_progress(self, done: int, total: int) -> None:
        return

    def tts_progress(self, done: int, total: int) -> None:
        return

    def merge_progress(self, ratio: float) -> None:
        return


class CallbackDubbingReporter:
    """Lightweight reporter built from callables (used by the background worker)."""

    def __init__(
        self,
        *,
        check_cancel: Callable[[], None],
        check_pause: Callable[[], None],
        stage: Callable[[str, float], None],
        translate_progress: Optional[Callable[[int, int], None]] = None,
        tts_progress: Optional[Callable[[int, int], None]] = None,
        merge_progress: Optional[Callable[[float], None]] = None,
    ):
        self._check_cancel = check_cancel
        self._check_pause = check_pause
        self._stage = stage
        self._translate_progress = translate_progress or (lambda _d, _t: None)
        self._tts_progress = tts_progress or (lambda _d, _t: None)
        self._merge_progress = merge_progress or (lambda _r: None)

    def check_cancel(self) -> None:
        self._check_cancel()

    def check_pause(self) -> None:
        self._check_pause()

    def stage(self, message: str, progress: float) -> None:
        self._stage(message, progress)

    def translate_progress(self, done: int, total: int) -> None:
        self._translate_progress(done, total)

    def tts_progress(self, done: int, total: int) -> None:
        self._tts_progress(done, total)

    def merge_progress(self, ratio: float) -> None:
        self._merge_progress(ratio)
