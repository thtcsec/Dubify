"""Header/footer branding and HyperFrames-inspired social overlays for Studio."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from PIL import Image, ImageDraw, ImageFont

SocialOverlayPreset = Literal["none", "tiktok_follow", "yt_lower_third"]


@dataclass
class BrandingBand:
    enabled: bool = False
    text: str = ""
    image_path: Optional[Path] = None
    opacity: float = 0.85


@dataclass
class StudioBranding:
    header: BrandingBand
    footer: BrandingBand


@dataclass
class StudioLayout:
    """Percent-based overlay positions (synced with frontend StudioLayoutPreview)."""

    header_y_pct: float = 0.0
    footer_y_pct: float = 89.0
    social_left_pct: float = 4.4
    social_bottom_pct: float = 6.25
    caption_y_pct: float = 64.0


def _pct(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_studio_layout(payload: dict[str, Any], *, aspect_ratio: str = "9:16") -> StudioLayout:
    parts = (aspect_ratio or "9:16").split(":")
    portrait = len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and int(parts[1]) > int(parts[0])
    defaults = StudioLayout(
        footer_y_pct=89.0 if portrait else 88.0,
        social_bottom_pct=6.25 if portrait else 5.0,
        caption_y_pct=64.0 if portrait else 78.0,
    )
    return StudioLayout(
        header_y_pct=max(0.0, min(_pct(payload.get("header_y_pct"), defaults.header_y_pct), 30.0)),
        footer_y_pct=max(50.0, min(_pct(payload.get("footer_y_pct"), defaults.footer_y_pct), 95.0)),
        social_left_pct=max(0.0, min(_pct(payload.get("social_left_pct"), defaults.social_left_pct), 80.0)),
        social_bottom_pct=max(1.0, min(_pct(payload.get("social_bottom_pct"), defaults.social_bottom_pct), 92.0)),
        caption_y_pct=max(22.0, min(_pct(payload.get("caption_y_pct"), defaults.caption_y_pct), 85.0)),
    )


def parse_studio_branding(payload: dict[str, Any]) -> StudioBranding:
    def band(prefix: str) -> BrandingBand:
        enabled = str(payload.get(f"{prefix}_enabled", "false")).lower() in ("1", "true", "yes")
        text = str(payload.get(f"{prefix}_text") or "").strip()
        opacity_raw = payload.get(f"{prefix}_opacity", 0.85)
        try:
            opacity = float(opacity_raw)
        except (TypeError, ValueError):
            opacity = 0.85
        opacity = max(0.05, min(opacity, 1.0))
        image_key = f"{prefix}_image_path"
        image_path = Path(payload[image_key]) if payload.get(image_key) else None
        if image_path and not image_path.exists():
            image_path = None
        if enabled and not text and not image_path:
            enabled = False
        return BrandingBand(enabled=enabled, text=text, image_path=image_path, opacity=opacity)

    return StudioBranding(header=band("header"), footer=band("footer"))


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    import os

    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    names = ["arialbd.ttf", "Arial Bold.ttf"] if bold else ["arial.ttf", "Arial.ttf", "segoeui.ttf"]
    for name in names:
        path = windir / "Fonts" / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), max(size, 10))
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        box = draw.textbbox((0, 0), trial, font=font)
        if current and box[2] - box[0] > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or [text[:80]]


def render_branding_png(
    *,
    width: int,
    height: int,
    band: BrandingBand,
    band_height: int,
    position: str,
) -> Image.Image:
    """RGBA strip for header (top) or footer (bottom)."""
    canvas = Image.new("RGBA", (width, band_height), (0, 0, 0, 0))
    alpha = int(255 * band.opacity)
    bar = Image.new("RGBA", (width, band_height), (8, 12, 24, int(alpha * 0.55)))
    canvas = Image.alpha_composite(canvas, bar)

    pad_x = int(width * 0.05)
    if band.image_path and band.image_path.exists():
        try:
            logo = Image.open(band.image_path).convert("RGBA")
            max_h = int(band_height * 0.72)
            max_w = int(width * 0.35)
            scale = min(max_w / logo.width, max_h / logo.height, 1.0)
            logo = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.Resampling.LANCZOS)
            if logo.mode == "RGBA":
                r, g, b, a = logo.split()
                a = a.point(lambda p: int(p * band.opacity))
                logo = Image.merge("RGBA", (r, g, b, a))
            x = pad_x
            y = (band_height - logo.height) // 2
            canvas.paste(logo, (x, y), logo)
            pad_x = x + logo.width + 24
        except Exception:
            pass

    if band.text:
        draw = ImageDraw.Draw(canvas)
        font_size = max(22, int(band_height * 0.32))
        font = _load_font(font_size, bold=True)
        lines = _wrap_text(draw, band.text, font, width - pad_x - int(width * 0.05))[:2]
        line_h = int(font_size * 1.25)
        total_h = line_h * len(lines)
        start_y = (band_height - total_h) // 2
        for i, line in enumerate(lines):
            draw.text(
                (pad_x, start_y + i * line_h),
                line,
                fill=(255, 255, 255, alpha),
                font=font,
            )

    return canvas


def branding_active(branding: StudioBranding) -> bool:
    return branding.header.enabled or branding.footer.enabled


@dataclass
class SocialOverlayConfig:
    preset: SocialOverlayPreset = "none"
    handle: str = ""
    subtitle: str = ""
    avatar_url: Optional[str] = None


def parse_social_overlay(payload: dict[str, Any]) -> SocialOverlayConfig:
    raw = str(payload.get("social_overlay") or "none").strip().lower()
    preset: SocialOverlayPreset = (
        raw if raw in ("none", "tiktok_follow", "yt_lower_third") else "none"
    )
    handle = str(payload.get("social_handle") or payload.get("social_overlay_handle") or "").strip()
    subtitle = str(payload.get("social_subtitle") or "").strip()
    avatar_key = payload.get("social_avatar_path")
    avatar_path = Path(avatar_key) if avatar_key else None
    if avatar_path and not avatar_path.exists():
        avatar_path = None
    if preset != "none" and not handle and preset == "tiktok_follow":
        handle = "@dubify"
    if preset == "yt_lower_third" and not subtitle:
        subtitle = "Subscribe for more"
    return SocialOverlayConfig(
        preset=preset,
        handle=handle,
        subtitle=subtitle,
        avatar_url=avatar_path.resolve().as_uri() if avatar_path else None,
    )


def social_overlay_html(
    config: SocialOverlayConfig,
    layout: StudioLayout | None = None,
) -> str:
    """HTML snippet injected into studio templates ({SOCIAL_OVERLAY})."""
    if config.preset == "none":
        return ""

    layout = layout or StudioLayout()
    pos_style = (
        f"left:{layout.social_left_pct:.2f}%;bottom:{layout.social_bottom_pct:.2f}%;"
        "right:auto;top:auto;"
    )

    if config.preset == "tiktok_follow":
        handle = html.escape(config.handle or "@channel")
        avatar = config.avatar_url or ""
        avatar_block = (
            f'<img class="tt-avatar" src="{html.escape(avatar, quote=True)}" alt=""/>'
            if avatar
            else '<div class="tt-avatar tt-avatar-fallback"></div>'
        )
        return f"""
<div class="social-overlay tiktok-follow" style="{pos_style}" aria-hidden="true">
  {avatar_block}
  <div class="tt-meta">
    <span class="tt-handle">{handle}</span>
    <span class="tt-follow-btn">Follow</span>
  </div>
</div>""".strip()

    if config.preset == "yt_lower_third":
        title = html.escape(config.handle or "Dubify Channel")
        sub = html.escape(config.subtitle or "Subscribe")
        avatar = config.avatar_url or ""
        avatar_block = (
            f'<img class="yt-avatar" src="{html.escape(avatar, quote=True)}" alt=""/>'
            if avatar
            else '<div class="yt-avatar yt-avatar-fallback"></div>'
        )
        return f"""
<div class="social-overlay yt-lower-third" style="{pos_style}" aria-hidden="true">
  {avatar_block}
  <div class="yt-text">
    <span class="yt-channel">{title}</span>
    <span class="yt-subline">{sub}</span>
  </div>
  <span class="yt-subscribe">Subscribe</span>
</div>""".strip()

    return ""
