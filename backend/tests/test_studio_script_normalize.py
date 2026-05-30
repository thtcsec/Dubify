from app.utils.studio_script_format import (
    normalize_studio_script_structure,
    script_needs_format_pass,
    strip_popup_markers_for_tts,
    strip_section_markers_for_tts,
)


def test_normalize_inline_hook_and_scene():
    raw = (
        "[Hook] Welcome to our video on Nestle. [STAT: 1.4M children] "
        "Scene 1: Child labor scandal. More facts here."
    )
    out = normalize_studio_script_structure(raw)
    assert "\n[Hook]\n" in out or out.startswith("[Hook]")
    assert "Scene 1:" not in out
    assert "[STAT:" in out


def test_script_needs_format_pass_detects_run_on():
    assert script_needs_format_pass("[Hook] " + "x" * 120)


def test_tts_strips_hook_and_scene_labels():
    text = "[Hook]\nNestle đang gặp scandal.\n[Cảnh 2]\nThêm chi tiết."
    spoken = strip_section_markers_for_tts(text)
    assert "Hook" not in spoken
    assert "Nestle" in spoken

    with_stat = "[Hook]\nLine [STAT: 42% — growth] ok."
    spoken2 = strip_popup_markers_for_tts(with_stat)
    assert "STAT" not in spoken2
    assert "42%" not in spoken2
    assert "Line" in spoken2
