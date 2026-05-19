from app.utils.hyperframes_render import wrap_scene_as_composition


def test_wrap_composition_includes_data_attributes():
    scene = """<!DOCTYPE html><html><body><div class="scene">Hello</div></body></html>"""
    wrapped = wrap_scene_as_composition(scene, width=1080, height=1920, duration=3.0)
    assert 'data-composition-id="dubify-scene"' in wrapped
    assert 'data-width="1080"' in wrapped
    assert 'data-height="1920"' in wrapped
    assert "window.__timelines" in wrapped
    assert "const duration = 3" in wrapped
