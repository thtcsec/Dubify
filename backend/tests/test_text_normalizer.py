from app.services.text_normalizer import normalize_for_tts


def test_light_normalize_preserves_vietnamese_words():
    text = "đây ai không còn chỉ là công nghệ"
    out = normalize_for_tts(text, "vi", transliterate=False)
    assert "đây" in out
    assert "công nghệ" in out


def test_light_normalize_strips_smart_quotes():
    text = "’đây ai’ không còn"
    out = normalize_for_tts(text, "vi", transliterate=False)
    assert "đây" in out
    assert "’" not in out
