from app.utils.studio_overlay import parse_studio_layout, social_overlay_html
from app.utils.studio_overlay import SocialOverlayConfig, StudioLayout


def test_parse_studio_layout_clamps():
    layout = parse_studio_layout(
        {
            "header_y_pct": 99,
            "footer_y_pct": 10,
            "caption_y_pct": 200,
        },
        aspect_ratio="9:16",
    )
    assert layout.header_y_pct <= 30
    assert layout.footer_y_pct >= 50
    assert layout.caption_y_pct <= 85


def test_social_overlay_uses_layout_position():
    html = social_overlay_html(
        SocialOverlayConfig(preset="tiktok_follow", handle="@test"),
        StudioLayout(social_left_pct=12.5, social_bottom_pct=8.0),
    )
    assert 'left:12.50%' in html
    assert 'bottom:8.00%' in html
