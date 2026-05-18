from app.utils.studio_scenes import parse_studio_scenes


def test_parse_bracket_sections():
    text = """[Mở đầu]
Hello world.

[Phần hai]
More text here."""
    scenes = parse_studio_scenes(text)
    assert len(scenes) == 2
    assert scenes[0].title == "Mở đầu"
    assert "Hello" in scenes[0].body
    assert scenes[1].title == "Phần hai"
