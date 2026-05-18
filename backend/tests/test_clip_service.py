from app.services.clip_service import ClipService


def test_plan_fixed_clips():
    clips = ClipService.plan_clips(125.0, max_duration=60.0, mode="fixed")
    assert len(clips) == 3
    assert clips[0].start == 0.0
    assert clips[-1].end == 125.0


def test_plan_scene_clips_by_cues():
    cues = [
        {"start": 0.0, "end": 25.0},
        {"start": 25.0, "end": 50.0},
        {"start": 50.0, "end": 80.0},
        {"start": 80.0, "end": 130.0},
    ]
    clips = ClipService.plan_clips(130.0, max_duration=60.0, mode="scene", cues=cues)
    assert len(clips) >= 2
    assert all(c.end - c.start <= 60.5 for c in clips)
