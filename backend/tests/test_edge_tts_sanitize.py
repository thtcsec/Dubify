from app.services.tts_service import TTSService


def test_sanitize_removes_empty_brackets():
    assert TTSService._sanitize_for_edge_tts("[]") == ""
    assert TTSService._sanitize_for_edge_tts("[") == ""


def test_sanitize_unwraps_section_labels():
    assert "Mo dau" in TTSService._sanitize_for_edge_tts("[Mo dau] noi dung canh")


def test_strip_studio_section_markers():
    script = "[Mo dau]\nNoi dung canh mot.\n\n[Canh hai]\nNoi dung hai."
    stripped = TTSService._strip_studio_section_markers(script)
    assert "[Mo dau]" not in stripped
    assert "Noi dung canh mot" in stripped
    assert "Noi dung hai" in stripped
