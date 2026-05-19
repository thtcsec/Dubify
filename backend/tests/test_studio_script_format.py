from app.utils.studio_script_format import (
    clean_llm_studio_output,
    extract_popups_from_text,
    normalize_popup_markers,
    strip_popup_markers_for_tts,
)


def test_normalize_popup_markers():
    raw = "Line {{stat: 47% growth}} here"
    assert "[STAT: 47% growth]" in normalize_popup_markers(raw)


def test_strip_popup_for_tts():
    text = "Hello [STAT: 2 billion users] world [DEF: AI — assistant]"
    assert "STAT" not in strip_popup_markers_for_tts(text)
    assert "Hello" in strip_popup_markers_for_tts(text)


def test_extract_popups():
    items = extract_popups_from_text("[STAT: 10x] fast\n[DEF: LLM — large model]")
    assert len(items) == 2
    assert items[0]["type"] == "stat"
