"""Timeline Schema — canonical JSON structure for scene graph / timeline.

Requirement 9: Single source of truth between Studio Editor UI and render pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class TransitionType(str, Enum):
    FADE = "fade"
    SMOOTHLEFT = "smoothleft"
    SMOOTHRIGHT = "smoothright"
    SLIDEUP = "slideup"
    SLIDERIGHT = "slideright"
    FADEBLACK = "fadeblack"
    WIPERIGHT = "wiperight"
    WIPELEFT = "wipeleft"
    DISSOLVE = "dissolve"
    ZOOMIN = "zoomin"
    SLIDELEFT = "slideleft"
    FADEWHITE = "fadewhite"


@dataclass
class AudioTrack:
    """Audio track in the timeline."""
    id: str
    path: str  # relative or absolute path
    start: float = 0.0
    duration: float = 0.0
    volume: float = 1.0
    type: str = "voiceover"  # voiceover, bgm, sfx


@dataclass
class SceneLayer:
    """A visual layer within a scene."""
    id: str
    type: str  # image, text, overlay, lottie
    content: str = ""  # text content or file path
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0  # percentage
    height: float = 100.0
    opacity: float = 1.0
    animation: str = ""  # CSS animation name
    z_index: int = 0


@dataclass
class SceneTransition:
    """Transition between scenes."""
    type: TransitionType = TransitionType.FADE
    duration: float = 0.65  # seconds


@dataclass
class TimelineScene:
    """A single scene in the timeline."""
    scene_id: str
    start: float  # seconds
    duration: float  # seconds
    template: str = "tiktok_news"
    title: str = ""
    body: str = ""
    image_path: str = ""
    layers: List[SceneLayer] = field(default_factory=list)
    audio_tracks: List[AudioTrack] = field(default_factory=list)
    transition_in: Optional[SceneTransition] = None
    transition_out: Optional[SceneTransition] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineProject:
    """Complete timeline project — the canonical intermediate representation."""
    project_id: str
    duration: float  # total duration in seconds
    fps: int = 30
    width: int = 1080
    height: int = 1920
    aspect_ratio: str = "9:16"
    scenes: List[TimelineScene] = field(default_factory=list)
    audio_tracks: List[AudioTrack] = field(default_factory=list)  # global tracks (BGM)
    metadata: Dict[str, Any] = field(default_factory=dict)
    seed: int = 42  # for reproducible randomness

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineProject":
        """Deserialize from dict (basic validation)."""
        scenes = []
        for s in data.get("scenes", []):
            layers = [SceneLayer(**l) for l in s.pop("layers", [])]
            audio = [AudioTrack(**a) for a in s.pop("audio_tracks", [])]
            t_in = SceneTransition(**s.pop("transition_in")) if s.get("transition_in") else None
            t_out = SceneTransition(**s.pop("transition_out")) if s.get("transition_out") else None
            scenes.append(TimelineScene(
                **{k: v for k, v in s.items() if k in TimelineScene.__dataclass_fields__},
                layers=layers,
                audio_tracks=audio,
                transition_in=t_in,
                transition_out=t_out,
            ))

        global_audio = [AudioTrack(**a) for a in data.get("audio_tracks", [])]

        return cls(
            project_id=data.get("project_id", ""),
            duration=data.get("duration", 0.0),
            fps=data.get("fps", 30),
            width=data.get("width", 1080),
            height=data.get("height", 1920),
            aspect_ratio=data.get("aspect_ratio", "9:16"),
            scenes=scenes,
            audio_tracks=global_audio,
            metadata=data.get("metadata", {}),
            seed=data.get("seed", 42),
        )

    def validate(self) -> List[str]:
        """Validate timeline structure. Returns list of issues (empty = valid)."""
        issues = []
        if not self.project_id:
            issues.append("Missing project_id")
        if self.duration <= 0:
            issues.append("Duration must be positive")
        if not self.scenes:
            issues.append("No scenes defined")
        for i, scene in enumerate(self.scenes):
            if scene.duration <= 0:
                issues.append(f"Scene {i} has non-positive duration")
            if scene.start < 0:
                issues.append(f"Scene {i} has negative start time")
        return issues
