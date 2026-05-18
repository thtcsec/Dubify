from app.utils.studio_overlay import branding_active, parse_studio_branding, render_branding_png


def test_parse_branding_disabled_by_default():
    branding = parse_studio_branding({})
    assert not branding_active(branding)


def test_parse_branding_header_text():
    branding = parse_studio_branding(
        {"header_enabled": True, "header_text": "Dubify News", "header_opacity": 0.7}
    )
    assert branding.header.enabled
    assert branding.header.text == "Dubify News"
    assert branding.header.opacity == 0.7
    assert branding_active(branding)


def test_render_branding_png_dimensions():
    band = parse_studio_branding(
        {"footer_enabled": True, "footer_text": "Subscribe", "footer_opacity": 0.5}
    ).footer
    img = render_branding_png(width=1080, height=120, band=band, band_height=120, position="footer")
    assert img.size == (1080, 120)
    assert img.mode == "RGBA"
