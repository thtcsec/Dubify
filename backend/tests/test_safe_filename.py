from app.utils.safe_filename import dubbed_output_filename, safe_basename, studio_output_filename


def test_safe_basename_truncates_long_title():
    long_title = "KHOA HỌC, CÔNG NGHỆ, ĐỔI MỚI SÁNG TẠO VÀ CHUYỂN ĐỔI SỐ" * 3
    out = safe_basename(long_title, max_len=48)
    assert len(out) <= 48
    assert "KHOA" in out


def test_dubbed_output_filename():
    name = dubbed_output_filename("url_abc123", "My Video Title.mp4")
    assert name.startswith("url_abc123_dubbed_")
    assert name.endswith(".mp4")
    assert " " not in name or len(name) < 80


def test_studio_output_filename():
    name = studio_output_filename("studio_abcd", "Google I/O 2024")
    assert name.startswith("studio_abcd_")
    assert name.endswith(".mp4")
