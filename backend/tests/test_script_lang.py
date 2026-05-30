from app.utils.script_lang import lang_instruction, spoken_content_looks_wrong_lang


def test_lang_instruction_vi():
    assert "Vietnamese" in lang_instruction("vi")
    assert "tiếng Việt" in lang_instruction("vi-VN")


def test_spoken_wrong_lang_english_when_vi_requested():
    en_script = (
        "[Hook]\n"
        "Google I/O is the annual developer conference where Google announces Android and AI.\n"
        "Developers from around the world attend the keynote for the latest technology news.\n"
        "[Cảnh 2]\n"
        "This year the conference featured major updates for developers and partners worldwide."
    )
    assert spoken_content_looks_wrong_lang(en_script, "vi") is True


def test_spoken_ok_vietnamese():
    vi_script = (
        "[Hook]\n"
        "Google I/O 2024 mang đến hàng loạt tin Android và Gemini cho nhà phát triển.\n"
        "[STAT: 2 tỷ — thiết bị Android]\n"
        "Sự kiện diễn ra tại Mountain View với keynote kéo dài hơn hai giờ."
    )
    assert spoken_content_looks_wrong_lang(vi_script, "vi") is False
