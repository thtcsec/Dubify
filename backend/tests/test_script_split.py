from app.utils.script_split import split_spoken_lines


def test_split_by_sentence():
    lines = split_spoken_lines("Xin chào. Hôm nay trời đẹp! Bạn khỏe không?")
    assert len(lines) == 3
    assert lines[0] == "Xin chào."
