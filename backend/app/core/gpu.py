"""GPU / NVENC helpers — prefer RTX CUDA when available."""

from __future__ import annotations

import logging
import shutil
import subprocess
from functools import lru_cache
from typing import Literal

from app.core.config import settings

logger = logging.getLogger(__name__)

_nvenc_checked: bool | None = None
_nvenc_available: bool = False


def torch_cuda_available() -> bool:
    if not settings.use_gpu():
        return False
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_torch_device() -> str:
    """Device for PyTorch models (Whisper, NLLB)."""
    pref = (settings.WHISPER_DEVICE or "auto").strip().lower()
    if pref == "cpu":
        return "cpu"
    if pref == "cuda":
        return "cuda" if torch_cuda_available() else "cpu"
    return "cuda" if torch_cuda_available() else "cpu"


def resolve_whisper_device() -> str:
    return resolve_torch_device()


@lru_cache(maxsize=1)
def nvenc_available() -> bool:
    global _nvenc_checked, _nvenc_available
    if _nvenc_checked:
        return _nvenc_available
    _nvenc_checked = True
    if not settings.use_gpu():
        _nvenc_available = False
        return False
    enc = (settings.VIDEO_ENCODER or "auto").strip().lower()
    if enc == "cpu" or enc == "libx264":
        _nvenc_available = False
        return False
    if enc == "nvenc":
        _nvenc_available = shutil.which("ffmpeg") is not None
        return _nvenc_available
    if not shutil.which("ffmpeg"):
        _nvenc_available = False
        return False
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        _nvenc_available = "h264_nvenc" in (proc.stdout or "")
    except Exception:
        _nvenc_available = False
    return _nvenc_available


def video_encoder_args(*, crf: int = 22) -> list[str]:
    """FFmpeg video encode flags — NVENC on RTX when enabled."""
    if nvenc_available():
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-rc",
            "vbr",
            "-cq",
            str(max(18, min(crf, 32))),
            "-b:v",
            "0",
        ]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", str(crf)]


def log_gpu_status() -> None:
    device = resolve_torch_device()
    cuda = torch_cuda_available()
    nvenc = nvenc_available()
    gpu_name = ""
    if cuda:
        try:
            import torch

            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "CUDA"
    logger.info(
        "GPU status: torch=%s (%s), video_encoder=%s, USE_GPU=%s",
        device,
        gpu_name or "n/a",
        "h264_nvenc" if nvenc else "libx264",
        settings.use_gpu(),
    )


def gpu_info_dict() -> dict:
    return {
        "use_gpu": settings.use_gpu(),
        "torch_device": resolve_torch_device(),
        "cuda_available": torch_cuda_available(),
        "video_encoder": "h264_nvenc" if nvenc_available() else "libx264",
        "whisper_device": resolve_whisper_device(),
    }
