from pathlib import Path

from app.utils.template_fill import fill_template


def test_fill_single_brace_placeholders():
    tpl = '<img src="{IMAGE_URL}"/><p>{TEXT}</p>'
    out = fill_template(tpl, {"IMAGE_URL": "file:///bg.png", "TEXT": "Xin chao"})
    assert "{TEXT}" not in out
    assert "{IMAGE_URL}" not in out
    assert "Xin chao" in out
    assert "file:///bg.png" in out


def test_tiktok_template_on_disk_has_no_literal_text_placeholder():
    path = Path(__file__).resolve().parent.parent / "templates/studio/1080x1920/tiktok_news.html"
    if not path.exists():
        return
    filled = fill_template(
        path.read_text(encoding="utf-8"),
        {"IMAGE_URL": "x", "TITLE_BLOCK": "<h1>T</h1>", "TEXT": "Noi dung canh"},
    )
    assert "{TEXT}" not in filled
    assert "Noi dung canh" in filled
