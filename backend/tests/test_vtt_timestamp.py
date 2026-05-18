from app.services.video_service import VideoService


def test_parse_comma_milliseconds():
    assert VideoService._parse_media_timestamp("00:00:01,500") == 1.5


def test_parse_dot_milliseconds():
    assert VideoService._parse_media_timestamp("00:00:02.250") == 2.25


def test_parse_without_fraction():
    assert VideoService._parse_media_timestamp("00:01:03") == 63.0


def test_parse_vtt_edge_style(tmp_path):
    vtt = tmp_path / "test.vtt"
    vtt.write_text(
        "WEBVTT\n\n"
        "1\n"
        "00:00:00.000 --> 00:00:02,500\n"
        "Hello world\n",
        encoding="utf-8",
    )
    cues = VideoService._parse_vtt(vtt)
    assert len(cues) == 1
    assert cues[0][0] == 0.0
    assert abs(cues[0][1] - 2.5) < 0.01
