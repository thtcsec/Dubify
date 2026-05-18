from app.utils.subtitles import wrap_subtitle_text
from app.services.asr_service import ASRService


def test_wrap_subtitle_splits_long_line():
    text = "This is a very long subtitle line that should wrap onto two rows for readability."
    wrapped = wrap_subtitle_text(text, max_chars=36, max_lines=2)
    lines = wrapped.split("\n")
    assert len(lines) == 2
    assert all(len(line) <= 40 for line in lines)


def test_split_oversized_segments():
    segments = [
        {
            "text": "word " * 40,
            "start": 0.0,
            "end": 12.0,
        }
    ]
    out = ASRService.split_oversized_segments(segments, max_chars=40, max_duration=6.0)
    assert len(out) >= 2
    assert out[0]["start"] == 0.0
    assert abs(out[-1]["end"] - 12.0) < 0.01
