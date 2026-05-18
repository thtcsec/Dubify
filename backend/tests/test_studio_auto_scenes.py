from app.utils.studio_scenes import auto_split_body_into_scenes, parse_studio_scenes


def test_auto_split_long_script_without_markers():
    body = (
        "AI không còn chỉ là công nghệ. "
        "Nó đang trở thành vấn đề của cả nhân loại. "
        "Ngày hôm nay Vatican thông báo một câu hỏi rất thẳng. "
        "Chúng ta cần suy nghĩ lại về đạo đức và trách nhiệm."
    )
    chunks = auto_split_body_into_scenes(body)
    assert len(chunks) >= 3

    scenes = parse_studio_scenes(body)
    assert len(scenes) >= 3


def test_section_markers_not_auto_split():
    script = "[Mở đầu]\nDòng một.\n\n[Phần hai]\nDòng hai."
    scenes = parse_studio_scenes(script)
    assert len(scenes) == 2
    assert scenes[0].title == "Mở đầu"
