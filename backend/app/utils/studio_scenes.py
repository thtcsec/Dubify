"""Parse studio scripts into titled scenes (Pixelle-Video-style [section] blocks)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils.script_split import split_spoken_lines

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$", re.MULTILINE)
_MAX_AUTO_SCENES = 7
_MIN_CHARS_AUTO_SPLIT = 80


def auto_split_body_into_scenes(body: str, max_scenes: int = _MAX_AUTO_SCENES) -> list[str]:
    """Split a script without [Section] markers into multiple visual scenes."""
    cleaned = (body or "").strip()
    if not cleaned or len(cleaned) < _MIN_CHARS_AUTO_SPLIT:
        return [cleaned] if cleaned else []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs[:max_scenes]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", cleaned) if s.strip()]
    if len(sentences) <= 2:
        return [cleaned]

    target_scenes = min(max_scenes, max(3, len(cleaned) // 90))
    if len(sentences) >= 4:
        per_chunk = 1
    else:
        per_chunk = max(1, (len(sentences) + target_scenes - 1) // target_scenes)
    chunks: list[str] = []
    for i in range(0, len(sentences), per_chunk):
        chunk = " ".join(sentences[i : i + per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks[:max_scenes] or [cleaned]


@dataclass
class StudioScene:
    title: str
    body: str
    lines: list[str]

    @property
    def line_count(self) -> int:
        return len(self.lines)


def parse_studio_scenes(text: str, max_chars_per_line: int = 90) -> list[StudioScene]:
    """Split script on [Section Title] markers; fallback to a single scene."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    matches = list(_SECTION_RE.finditer(cleaned))
    scenes: list[StudioScene] = []

    if not matches:
        for chunk in auto_split_body_into_scenes(cleaned):
            scenes.append(
                StudioScene(
                    title="",
                    body=chunk,
                    lines=split_spoken_lines(chunk, max_chars=max_chars_per_line),
                )
            )
        return scenes

    if matches[0].start() > 0:
        intro = cleaned[: matches[0].start()].strip()
        if intro:
            scenes.append(
                StudioScene(
                    title="",
                    body=intro,
                    lines=split_spoken_lines(intro, max_chars=max_chars_per_line),
                )
            )

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        body = cleaned[body_start:body_end].strip()
        if not body and not title:
            continue
        scenes.append(
            StudioScene(
                title=title,
                body=body,
                lines=split_spoken_lines(body, max_chars=max_chars_per_line) or [title],
            )
        )

    return scenes


def assign_scene_timings(
    scenes: list[StudioScene],
    cue_starts: list[float],
    cue_ends: list[float],
    total_duration: float,
) -> list[dict]:
    """Map sequential TTS/VTT cues onto scenes by line count."""
    timed: list[dict] = []
    cursor = 0
    n_cues = len(cue_starts)

    for scene in scenes:
        count = max(scene.line_count, 1)
        slice_start = cursor
        slice_end = min(cursor + count, n_cues)
        cursor = slice_end

        if slice_start < n_cues:
            start = cue_starts[slice_start]
            end = cue_ends[slice_end - 1] if slice_end > slice_start else total_duration
        elif timed:
            start = timed[-1]["end"]
            end = min(start + 2.0, total_duration)
        else:
            start = 0.0
            end = min(total_duration, 3.0)

        timed.append(
            {
                "title": scene.title,
                "body": scene.body,
                "start": max(0.0, start),
                "end": max(start + 0.35, end),
            }
        )

    if timed and timed[-1]["end"] < total_duration:
        timed[-1]["end"] = total_duration

    return timed


def assign_scene_timings_proportional(
    scenes: list[StudioScene],
    total_duration: float,
    min_scene: float = 4.0,
) -> list[dict]:
    """Split total audio duration across scenes by spoken content weight."""
    if not scenes or total_duration <= 0:
        return []

    weights = [max(len(scene.body or scene.title or ""), 40) for scene in scenes]
    weight_sum = sum(weights) or 1.0
    timed: list[dict] = []
    cursor = 0.0

    for index, scene in enumerate(scenes):
        share = weights[index] / weight_sum
        duration = max(min_scene, total_duration * share)
        if index == len(scenes) - 1:
            end = total_duration
        else:
            end = min(cursor + duration, total_duration)
        timed.append(
            {
                "title": scene.title,
                "body": scene.body,
                "start": cursor,
                "end": max(cursor + 0.5, end),
            }
        )
        cursor = timed[-1]["end"]

    if timed:
        timed[-1]["end"] = total_duration
    return timed


def scene_display_text(body: str, max_chars: int = 160) -> str:
    """Short on-screen excerpt (not the full narration block)."""
    cleaned = re.sub(r"\s+", " ", (body or "").strip())
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[: max_chars - 1].rsplit(" ", 1)[0]
    return (cut or cleaned[:max_chars]).rstrip(".,;:") + "…"
