"""Header/footer branding overlays for Studio videos."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont


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
