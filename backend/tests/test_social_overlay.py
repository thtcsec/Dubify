from app.utils.studio_overlay import parse_social_overlay, social_overlay_html


def test_parse_tiktok_follow_defaults():
    cfg = parse_social_overlay({"social_overlay": "tiktok_follow"})
    assert cfg.preset == "tiktok_follow"
    assert cfg.handle == "@dubify"
    html = social_overlay_html(cfg)
    assert "tiktok-follow" in html
    assert "@dubify" in html


def test_parse_yt_lower_third():
    cfg = parse_social_overlay(
        {
            "social_overlay": "yt_lower_third",
            "social_handle": "Dubify AI",
            "social_subtitle": "Subscribe now",
        }
    )
    html = social_overlay_html(cfg)
    assert "yt-lower-third" in html
    assert "Dubify AI" in html
    assert "Subscribe now" in html


def test_none_overlay_empty():
    assert social_overlay_html(parse_social_overlay({})) == ""
