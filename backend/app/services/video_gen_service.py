import logging
import time
from pathlib import Path
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoGenService:
    FAL_QUEUE_BASE = "https://queue.fal.run/fal-ai"
    SUPPORTED_PROVIDERS = {"veo3", "kling", "minimax", "seedance"}

    @staticmethod
    def _get_fal_key() -> str:
        key = settings.FAL_KEY or settings.FAL_AI_API_KEY
        if not key:
            raise RuntimeError("FAL_KEY is not configured.")
        return key

    @staticmethod
    def _fal_headers() -> dict[str, str]:
        return {
            "Authorization": f"Key {VideoGenService._get_fal_key()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _normalize_duration(provider: str, duration_seconds: int) -> Optional[str]:
        if provider == "veo3":
            return "8s"
        if provider == "kling":
            return "10" if duration_seconds >= 8 else "5"
        if provider == "seedance":
            if duration_seconds >= 12:
                return "15"
            if duration_seconds >= 9:
                return "10"
            return "8"
        return None

    @staticmethod
    def _build_fal_request(
        provider: str,
        prompt: str,
        aspect_ratio: str,
        duration_seconds: int,
    ) -> tuple[str, dict]:
        if provider not in VideoGenService.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported video provider: {provider}")

        if provider == "veo3":
            model_path = "veo3.1"
        elif provider == "kling":
            model_path = "kling/v3/standard/text-to-video"
        elif provider == "minimax":
            model_path = "minimax/hailuo-02/pro/text-to-video"
        else:
            model_path = "bytedance/seedance-2.0/text-to-video"

        payload: dict = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        duration = VideoGenService._normalize_duration(provider, duration_seconds)
        if duration:
            payload["duration"] = duration

        if provider == "veo3":
            payload["generate_audio"] = False

        return model_path, payload

    @staticmethod
    def _extract_video_url(result: dict) -> Optional[str]:
        video = result.get("video")
        if isinstance(video, dict):
            url = video.get("url")
            if url:
                return url

        for key in ("video_url", "url", "output"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict) and first.get("url"):
                    return first.get("url")

        return None

    def generate_fal_video(
        self,
        provider: str,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "9:16",
        duration_seconds: int = 0,
        timeout_seconds: int = 600,
    ) -> Path:
        headers = self._fal_headers()
        model_path, payload = self._build_fal_request(provider, prompt, aspect_ratio, duration_seconds)

        submit_resp = requests.post(
            f"{self.FAL_QUEUE_BASE}/{model_path}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        submit_resp.raise_for_status()
        queue_data = submit_resp.json()
        status_url = queue_data.get("status_url")
        response_url = queue_data.get("response_url")
        if not status_url or not response_url:
            raise RuntimeError("fal.ai queue response missing status_url/response_url")

        deadline = time.time() + timeout_seconds
        status = ""
        while time.time() < deadline:
            status_resp = requests.get(status_url, headers=headers, timeout=15)
            status_resp.raise_for_status()
            status = status_resp.json().get("status", "")
            if status == "COMPLETED":
                break
            if status in {"FAILED", "CANCELLED"}:
                raise RuntimeError(f"fal.ai generation {status.lower()}")
            time.sleep(5)

        if status != "COMPLETED":
            raise RuntimeError("fal.ai generation timed out")

        result_resp = requests.get(response_url, headers=headers, timeout=60)
        result_resp.raise_for_status()
        result_data = result_resp.json()
        video_url = self._extract_video_url(result_data)
        if not video_url:
            raise RuntimeError("fal.ai response missing video url")

        video_resp = requests.get(video_url, stream=True, timeout=120)
        video_resp.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)
        video_resp.close()
        logger.info("fal.ai video saved to %s", output_path)
        return output_path
