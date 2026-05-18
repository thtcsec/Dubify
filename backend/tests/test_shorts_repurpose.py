from app.services.clip_service import ClipService


def test_plan_clips_splits_long_video():
    clips = ClipService.plan_clips(125.0, max_duration=60.0, mode="fixed")
    assert len(clips) >= 2
    assert clips[0].label == "Part 1"
    assert clips[-1].end <= 125.0
