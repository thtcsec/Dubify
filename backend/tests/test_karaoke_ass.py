from pathlib import Path

from app.services.video_service import VideoService


def test_karaoke_ass_has_no_raw_k_tags():
    cues = [(0.0, 2.0, "đây là không chỉ là công nghệ")]
    ass = Path("test_karaoke_out.ass")
    try:
        VideoService._create_karaoke_ass(cues, ass, (1080, 1920))
        body = ass.read_text(encoding="utf-8")
        assert "{\\k" not in body
        assert "\\\\k" not in body
        assert "\\move(" not in body
        assert "đây" in body or "là" in body
        assert "Dialogue:" in body
    finally:
        ass.unlink(missing_ok=True)
