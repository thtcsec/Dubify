"""Human-in-the-loop PixVerse adapter scaffold for hackathon demos.

This module prepares 4-8 short shots from reviewed storyboard scenes and
converts them into PixVerse-friendly prompts. It also provides a local fallback
plan so the demo can continue if the remote API fails or times out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


MIN_SHOTS = 4
MAX_SHOTS = 8
MIN_SHOT_SECONDS = 5
MAX_SHOT_SECONDS = 8


@dataclass(slots=True)
class StoryboardScene:
    """A user-reviewed scene ready for visual generation."""

    scene_id: str
    description: str
    subject: str = ""
    action: str = ""
    camera_movement: str = "slow push in"
    lighting_style: str = "cinematic soft light"
    duration_seconds: int = 6
    approved: bool = True


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
        api_base: str = "https://api.pixverse.ai",
        timeout_seconds: int = 45,
    ) -> None:
        self.api_key = api_key.strip()
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = max(5, int(timeout_seconds))

    def build_plan(
        self,
        scenes: Iterable[StoryboardScene],
        aspect_ratio: str = "9:16",
    ) -> PixVerseRenderPlan:
        approved = [scene for scene in scenes if scene.approved]
        if not approved:
            raise ValueError("No approved storyboard scenes available for PixVerse.")
        if not MIN_SHOTS <= len(approved) <= MAX_SHOTS:
            raise ValueError(
                f"PixVerse storyboard must contain {MIN_SHOTS}-{MAX_SHOTS} approved shots."
            )

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

