"""Human-in-the-loop PixVerse adapter scaffold for hackathon demos.

This module prepares 4-8 short shots from reviewed storyboard scenes and
converts them into PixVerse-friendly prompts. It also provides a local fallback
plan so the demo can continue if the remote API fails or times out.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

import requests
import time


MIN_SHOTS = 4
MAX_SHOTS = 8
MIN_SHOT_SECONDS = 5
MAX_SHOT_SECONDS = 8


@dataclass(slots=True)
class StoryboardScene:
    """A user-reviewed scene ready for visual generation."""

    scene_id: str
    description: str
    title: str = ""
    subject: str = ""
    action: str = ""
    camera_movement: str = "slow push in"
    lighting_style: str = "cinematic soft light"
    duration_seconds: int = 6
    approved: bool = True
    prompt_override: str = ""
    force_fallback: bool = False


@dataclass(slots=True)
class PixVerseShot:
    """One prompt-ready short shot for PixVerse generation."""

    shot_id: str
    scene_id: str
    duration_seconds: int
    prompt: str
    fallback_asset: str


@dataclass(slots=True)
class PixVerseRenderPlan:
    """A multi-shot visual storytelling plan for the renderer."""

    aspect_ratio: str
    shots: list[PixVerseShot] = field(default_factory=list)


@dataclass(slots=True)
class PixVerseRenderResult:
    """Result returned to the pipeline, even on graceful fallback."""

    provider: str
    success: bool
    assets: list[str]
    fallback_used: bool
    message: str


class PixVerseAdapter:
    """Prepare PixVerse prompts with a deterministic local fallback path."""

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "https://app-api.pixverse.ai",
        timeout_seconds: int = 45,
    ) -> None:
        self.api_key = api_key.strip()
        normalized_base = (api_base or "").rstrip("/")
        if "api.pixverse.ai" in normalized_base and "app-api.pixverse.ai" not in normalized_base:
            normalized_base = normalized_base.replace("api.pixverse.ai", "app-api.pixverse.ai")
        self.api_base = normalized_base or "https://app-api.pixverse.ai"
        self.timeout_seconds = max(5, int(timeout_seconds))

    def build_plan(
        self,
        scenes: Iterable[StoryboardScene],
        aspect_ratio: str = "9:16",
    ) -> PixVerseRenderPlan:
        approved = self._normalize_storyboard([scene for scene in scenes if scene.approved])
        if not approved:
            raise ValueError("No approved storyboard scenes available for PixVerse.")

        shots = [
            PixVerseShot(
                shot_id=f"shot_{index + 1:02d}",
                scene_id=scene.scene_id,
                duration_seconds=self._normalize_duration(scene.duration_seconds),
                prompt=self.scene_to_prompt(scene),
                fallback_asset=self.local_fallback_asset(index, aspect_ratio),
            )
            for index, scene in enumerate(approved)
        ]
        return PixVerseRenderPlan(aspect_ratio=aspect_ratio, shots=shots)

    def scene_to_prompt(self, scene: StoryboardScene) -> str:
        """Convert a reviewed scene into a PixVerse-friendly prompt."""

        if scene.prompt_override.strip():
            return scene.prompt_override.strip()

        subject = (scene.subject or self._extract_subject(scene.description)).strip()
        action = (scene.action or self._extract_action(scene.description)).strip()
        camera = (scene.camera_movement or "slow push in").strip()
        style = (scene.lighting_style or "cinematic soft light").strip()
        description = " ".join((scene.description or "").split()).strip()

        return (
            f"Subject: {subject}. "
            f"Action: {action}. "
            f"Camera movement: {camera}. "
            f"Lighting and style: {style}. "
            f"Context: {description}."
        )

    def render_with_fallback(
        self,
        plan: PixVerseRenderPlan,
        submitter: Callable[[PixVerseShot], str] | None = None,
    ) -> PixVerseRenderResult:
        """Attempt remote generation and degrade gracefully on any failure."""

        if not self.api_key or submitter is None:
            return self._fallback_result(plan, "PixVerse API is not configured.")

        assets: list[str] = []
        try:
            for shot in plan.shots:
                asset = submitter(shot)
                if not asset:
                    raise RuntimeError(f"PixVerse returned empty output for {shot.shot_id}.")
                assets.append(asset)
        except Exception as exc:
            return self._fallback_result(plan, f"PixVerse failed, fallback enabled: {exc}")

        return PixVerseRenderResult(
            provider="pixverse",
            success=True,
            assets=assets,
            fallback_used=False,
            message="PixVerse multi-shot render plan completed.",
        )

    def generate_text_to_video(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration_seconds: int,
        output_path: Path,
        model: str = "v6",
        quality: str = "720p",
        seed: int = 0,
        water_mark: bool = False,
    ) -> Path:
        path, _prov = self.generate_text_to_video_with_provenance(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            output_path=output_path,
            model=model,
            quality=quality,
            seed=seed,
            water_mark=water_mark,
        )
        return path

    def generate_text_to_video_with_provenance(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration_seconds: int,
        output_path: Path,
        model: str = "v6",
        quality: str = "720p",
        seed: int = 0,
        water_mark: bool = False,
    ) -> tuple[Path, dict]:
        if not self.api_key:
            raise RuntimeError("PixVerse API key is missing.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        trace_id = str(uuid4())
        video_id, request_payload = self._submit_text_to_video(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            model=model,
            quality=quality,
            seed=seed,
            water_mark=water_mark,
            trace_id=trace_id,
        )
        url = self._poll_result_url(video_id, trace_id=trace_id)
        self._download_video(url, output_path)
        provenance = {
            "provider": "pixverse",
            "api_base": self.api_base,
            "trace_id": trace_id,
            "video_id": int(video_id),
            "result_url": url,
            "request": request_payload,
            "output_path": str(output_path),
            "output_bytes": int(output_path.stat().st_size) if output_path.exists() else 0,
        }
        sidecar = output_path.with_suffix(output_path.suffix + ".pixverse.json")
        sidecar.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path, provenance

    def _headers(self, trace_id: str) -> dict[str, str]:
        return {
            "API-KEY": self.api_key,
            "Ai-trace-id": trace_id,
            "ai-trace-id": trace_id,
            "Content-Type": "application/json",
        }

    def get_credit_balance(self) -> dict[str, int]:
        if not self.api_key:
            raise RuntimeError("PixVerse API key is missing.")

        url = f"{self.api_base}/openapi/v2/account/balance"
        trace_id = str(uuid4())
        resp = requests.get(
            url,
            headers={"API-KEY": self.api_key, "Ai-trace-id": trace_id, "ai-trace-id": trace_id},
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        if int(data.get("ErrCode", 0)) != 0:
            raise RuntimeError(f"PixVerse balance failed: {data.get('ErrMsg') or data}")

        payload = data.get("Resp") or {}
        return {
            "credit_monthly": int(payload.get("credit_monthly") or 0),
            "credit_package": int(payload.get("credit_package") or 0),
            "account_id": int(payload.get("account_id") or 0),
        }

    def _submit_text_to_video(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        duration_seconds: int,
        model: str,
        quality: str,
        seed: int,
        water_mark: bool,
        trace_id: str,
    ) -> tuple[int, dict]:
        url = f"{self.api_base}/openapi/v2/video/text/generate"
        payload = {
            "aspect_ratio": aspect_ratio,
            "duration": int(duration_seconds),
            "model": model,
            "prompt": prompt[:5000],
            "quality": quality,
            "seed": int(seed),
            "water_mark": bool(water_mark),
            "generate_audio_switch": False,
        }
        resp = requests.post(url, headers=self._headers(trace_id), json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json() or {}
        if int(data.get("ErrCode", 0)) != 0:
            raise RuntimeError(f"PixVerse submit failed: {data.get('ErrMsg') or data}")
        video_id = (data.get("Resp") or {}).get("video_id")
        if video_id is None:
            raise RuntimeError(f"PixVerse submit returned no video_id: {data}")
        return int(video_id), payload

    def _poll_result_url(self, video_id: int, *, trace_id: str) -> str:
        url = f"{self.api_base}/openapi/v2/video/result/{video_id}"
        deadline = time.time() + float(self.timeout_seconds)
        last_status = None
        last_err = ""

        while time.time() < deadline:
            resp = requests.get(
                url,
                headers={"API-KEY": self.api_key, "Ai-trace-id": trace_id, "ai-trace-id": trace_id},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json() or {}
            if int(data.get("ErrCode", 0)) != 0:
                last_err = str(data.get("ErrMsg") or data)
                time.sleep(1.5)
                continue

            detail = data.get("Resp") or {}
            status = int(detail.get("status", 0) or 0)
            last_status = status

            if status == 1:
                result_url = str(detail.get("url") or "").strip()
                if not result_url:
                    raise RuntimeError(f"PixVerse status success but empty url (video_id={video_id}).")
                return result_url

            if status in (7, 8):
                raise RuntimeError(f"PixVerse generation failed (status={status}, video_id={video_id}).")

            time.sleep(2.0)

        raise TimeoutError(f"PixVerse timed out (video_id={video_id}, last_status={last_status}, err={last_err}).")

    @staticmethod
    def _download_video(url: str, output_path: Path) -> None:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("PixVerse download produced empty file.")

    def local_fallback_asset(self, shot_index: int, aspect_ratio: str) -> str:
        """Return a deterministic local fallback target for smooth demo continuity."""

        safe_ratio = aspect_ratio.replace(":", "x")
        return f"storage/temp/pixverse_fallback_{safe_ratio}_shot_{shot_index + 1:02d}.mp4"

    def _fallback_result(
        self,
        plan: PixVerseRenderPlan,
        reason: str,
    ) -> PixVerseRenderResult:
        return PixVerseRenderResult(
            provider="local_fallback",
            success=False,
            assets=[shot.fallback_asset for shot in plan.shots],
            fallback_used=True,
            message=reason,
        )

    @staticmethod
    def _normalize_duration(duration_seconds: int) -> int:
        return max(MIN_SHOT_SECONDS, min(MAX_SHOT_SECONDS, int(duration_seconds or 6)))

    @staticmethod
    def _extract_subject(description: str) -> str:
        words = [word for word in description.replace(",", " ").split() if word]
        return " ".join(words[:6]) or "main subject"

    @staticmethod
    def _extract_action(description: str) -> str:
        lowered = " ".join(description.split()).strip().lower()
        return lowered[:80] or "subtle cinematic motion"

    def _normalize_storyboard(
        self,
        scenes: list[StoryboardScene],
    ) -> list[StoryboardScene]:
        items = [replace(scene) for scene in scenes if scene.approved]
        if not items:
            return []

        while len(items) < MIN_SHOTS:
            split_index = max(range(len(items)), key=lambda idx: len(items[idx].description or items[idx].title))
            left, right = self._split_scene(items[split_index])
            items[split_index:split_index + 1] = [left, right]

        if len(items) > MAX_SHOTS:
            head = items[: MAX_SHOTS - 1]
            tail = items[MAX_SHOTS - 1 :]
            merged_description = " ".join(filter(None, [scene.description for scene in tail])).strip()
            merged_title = " / ".join(filter(None, [scene.title for scene in tail[:2]])).strip() or "Final beats"
            merged = replace(
                tail[0],
                scene_id=f"{tail[0].scene_id}-merged",
                title=merged_title,
                description=merged_description,
                duration_seconds=max(
                    MIN_SHOT_SECONDS,
                    min(MAX_SHOT_SECONDS, sum(scene.duration_seconds for scene in tail)),
                ),
                prompt_override="",
            )
            items = head + [merged]

        return items

    def _split_scene(self, scene: StoryboardScene) -> tuple[StoryboardScene, StoryboardScene]:
        parts = self._split_description(scene.description or scene.title or "Main scene")
        left_text, right_text = parts
        left = replace(
            scene,
            scene_id=f"{scene.scene_id}-a",
            title=f"{scene.title or 'Scene'} A".strip(),
            description=left_text,
            duration_seconds=self._normalize_duration(max(MIN_SHOT_SECONDS, scene.duration_seconds // 2 or 5)),
            prompt_override="",
        )
        right = replace(
            scene,
            scene_id=f"{scene.scene_id}-b",
            title=f"{scene.title or 'Scene'} B".strip(),
            description=right_text,
            duration_seconds=self._normalize_duration(max(MIN_SHOT_SECONDS, scene.duration_seconds - left.duration_seconds)),
            prompt_override="",
        )
        return left, right

    @staticmethod
    def _split_description(description: str) -> tuple[str, str]:
        cleaned = " ".join(description.split()).strip()
        if not cleaned:
            return "Main visual beat.", "Supporting visual beat."

        sentences = [part.strip() for part in cleaned.replace("!", ".").replace("?", ".").split(".") if part.strip()]
        if len(sentences) >= 2:
            mid = max(1, len(sentences) // 2)
            left = ". ".join(sentences[:mid]).strip() + "."
            right = ". ".join(sentences[mid:]).strip() + "."
            return left, right

        words = cleaned.split()
        mid = max(1, len(words) // 2)
        left = " ".join(words[:mid]).strip()
        right = " ".join(words[mid:]).strip()
        return left or cleaned, right or cleaned
