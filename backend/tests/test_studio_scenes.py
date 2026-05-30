from app.utils.studio_scenes import parse_studio_scenes


def test_stat_def_are_not_scene_headers():
    text = """[Hook]
Hello.
[STAT: 42% — growth]
More here.
[DEF: Term — explain]
[Cảnh 2]
End."""
    scenes = parse_studio_scenes(text)
    titles = [s.title for s in scenes]
    assert "STAT: 42% — growth" not in titles
    assert "DEF: Term — explain" not in titles
    assert any("Hook" in t or t == "Hook" for t in titles)


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
