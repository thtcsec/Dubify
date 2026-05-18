"""Render Pixelle-style HTML scene cards to PNG (Playwright or PIL fallback)."""



from __future__ import annotations

import concurrent.futures
import html
import logging
from pathlib import Path



from PIL import Image, ImageDraw, ImageEnhance, ImageFont



from app.utils.studio_playwright import playwright_render_ready



logger = logging.getLogger(__name__)



TEMPLATE_ROOT = Path(__file__).resolve().parent.parent.parent / "templates" / "studio"



ASPECT_TO_FOLDER = {

    "9:16": "1080x1920",

    "3:4": "1080x1440",

    "16:9": "1920x1080",

    "4:3": "1440x1080",

    "1:1": "1080x1080",

}



ASPECT_TO_SIZE = {

    "9:16": (1080, 1920),

    "3:4": (1080, 1440),

    "16:9": (1920, 1080),

    "4:3": (1440, 1080),

    "1:1": (1080, 1080),

}





class StudioHtmlService:

    def __init__(self, aspect_ratio: str = "9:16", template_name: str = "tiktok_news") -> None:

        self.aspect_ratio = aspect_ratio if aspect_ratio in ASPECT_TO_SIZE else "9:16"

        self.template_name = template_name

        folder = ASPECT_TO_FOLDER.get(self.aspect_ratio, "1080x1920")

        self.template_path = TEMPLATE_ROOT / folder / f"{template_name}.html"

        if not self.template_path.exists():
            raise FileNotFoundError(
                f"Studio template missing for {self.aspect_ratio}: {self.template_path}"
            )

        self.width, self.height = ASPECT_TO_SIZE[self.aspect_ratio]

        self._playwright_checked = False



    def render_scene_png(
        self,
        *,
        title: str,
        text: str,
        image_path: Path,
        output_png: Path,
    ) -> bool:
        """Render in a worker thread so Playwright sync API works after asyncio TTS."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                self._render_scene_png_impl,
                title=title,
                text=text,
                image_path=image_path,
                output_png=output_png,
            ).result()

    def _render_scene_png_impl(
        self,
        *,
        title: str,
        text: str,
        image_path: Path,
        output_png: Path,
    ) -> bool:
        output_png.parent.mkdir(parents=True, exist_ok=True)
        html_path = output_png.with_suffix(".html")
        self._write_scene_html(html_path, title=title, text=text, image_path=image_path)

        if self._screenshot_playwright(html_path, output_png):
            return output_png.exists()

        logger.warning("Playwright render failed; using PIL fallback (install: playwright install chromium).")
        return self._render_pil_fallback(title=title, text=text, image_path=image_path, output_png=output_png)



    def _write_scene_html(self, html_path: Path, *, title: str, text: str, image_path: Path) -> None:

        if not self.template_path.exists():

            raise FileNotFoundError(f"Studio template not found: {self.template_path}")



        template = self.template_path.read_text(encoding="utf-8")

        image_uri = image_path.resolve().as_uri()

        title_block = _title_block_html(title, template_name=self.template_name)

        body_text = _format_body_text(text)



        from app.utils.template_fill import fill_template

        snippet = fill_template(
            template,
            {
                "IMAGE_URL": image_uri,
                "TITLE_BLOCK": title_block,
                "TEXT": body_text,
            },
        )

        html_path.write_text(snippet, encoding="utf-8")



    def _screenshot_playwright(self, html_path: Path, output_png: Path) -> bool:

        if not self._playwright_checked:

            self._playwright_checked = True

            playwright_render_ready(auto_install=True)



        try:

            from playwright.sync_api import sync_playwright

        except ImportError:

            return False



        try:

            with sync_playwright() as playwright:

                browser = playwright.chromium.launch(

                    headless=True,

                    args=["--disable-dev-shm-usage", "--font-render-hinting=medium"],

                )

                page = browser.new_page(

                    viewport={"width": self.width, "height": self.height},

                    device_scale_factor=1,

                )

                page.goto(html_path.resolve().as_uri(), wait_until="load", timeout=30_000)

                page.wait_for_selector(".scene", timeout=10_000)

                try:

                    page.wait_for_function(

                        "() => { const img = document.querySelector('.bg img'); "

                        "return !img || img.complete; }",

                        timeout=12_000,

                    )

                except Exception:

                    pass

                page.wait_for_timeout(1600)

                scene = page.locator(".scene").first

                scene.screenshot(path=str(output_png), type="png")

                browser.close()

            ok = output_png.exists() and output_png.stat().st_size > 8_000

            if ok:

                logger.info("Playwright scene PNG: %s (%d bytes)", output_png.name, output_png.stat().st_size)

            return ok

        except Exception as e:

            logger.warning("Playwright scene render failed: %s", e)

            return False



    def _render_pil_fallback(

        self,

        *,

        title: str,

        text: str,

        image_path: Path,

        output_png: Path,

    ) -> bool:

        try:

            w, h = self.width, self.height

            scale = h / 1920.0

            base = Image.open(image_path).convert("RGB")

            base = _cover_resize(base, w, h)

            base = ImageEnhance.Brightness(base).enhance(0.9)

            base = ImageEnhance.Color(base).enhance(1.15)

            overlay = Image.new("RGBA", (w, h), (15, 23, 42, 100))

            canvas = Image.alpha_composite(base.convert("RGBA"), overlay)

            draw = ImageDraw.Draw(canvas)

            font_title = _load_studio_font(int(76 * scale), bold=True)

            font_body = _load_studio_font(int(50 * scale), bold=False)



            pad_x = int(72 * scale)

            card_top = int(h * 0.52)

            card_h = int(h * 0.38)

            draw.rounded_rectangle(

                (pad_x, card_top, w - pad_x, card_top + card_h),

                radius=int(24 * scale),

                fill=(255, 255, 255, 38),

            )



            y = card_top + int(48 * scale)

            if title:

                for line in _wrap_lines(title, 20)[:2]:

                    draw.text((pad_x + int(32 * scale), y), line, fill=(255, 255, 255), font=font_title)

                    y += int(78 * scale)

                y += int(20 * scale)



            for line in _wrap_lines(text.replace("\n", " "), 26)[:5]:

                draw.text((pad_x + int(32 * scale), y), line, fill=(248, 250, 252), font=font_body)

                y += int(60 * scale)



            canvas.convert("RGB").save(output_png, "PNG")

            return True

        except Exception as e:

            logger.error("PIL studio fallback failed: %s", e)

            return False





def _title_block_html(title: str, *, template_name: str) -> str:

    if not title:

        return ""

    safe = html.escape(title)

    if template_name in ("tiktok_news", "news_scene"):

        return f'<h1 class="title">{safe}</h1><div class="bar"></div>'

    return (

        f'<div class="video-title-wrapper">'

        f'<h1 class="video-title">{safe}</h1>'

        f'<div class="title-underline"></div>'

        f'</div>'

    )





def _format_body_text(text: str) -> str:

    cleaned = (text or "").replace("\r", "").strip()

    if "\n" in cleaned:

        lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()][:5]

    else:

        lines = _wrap_lines(cleaned, 24)[:5]

    return html.escape("\n".join(lines))





def _cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:

    src_w, src_h = img.size

    scale = max(target_w / src_w, target_h / src_h)

    new_size = (int(src_w * scale), int(src_h * scale))

    resized = img.resize(new_size, Image.Resampling.LANCZOS)

    left = (resized.width - target_w) // 2

    top = (resized.height - target_h) // 2

    return resized.crop((left, top, left + target_w, top + target_h))





def _load_studio_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:

    import os



    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))

    candidates = (

        ["arialbd.ttf", "Arial Bold.ttf", "segoeuib.ttf"]

        if bold

        else ["arial.ttf", "Arial.ttf", "segoeui.ttf"]

    )

    for name in candidates:

        path = windir / "Fonts" / name

        if path.exists():

            try:

                return ImageFont.truetype(str(path), max(size, 12))

            except OSError:

                continue

    return ImageFont.load_default()





def _wrap_lines(text: str, max_chars: int) -> list[str]:

    words = text.split()

    lines: list[str] = []

    current: list[str] = []

    length = 0

    for word in words:

        extra = len(word) + (1 if current else 0)

        if current and length + extra > max_chars:

            lines.append(" ".join(current))

            current = [word]

            length = len(word)

        else:

            current.append(word)

            length += extra

    if current:

        lines.append(" ".join(current))

    return lines or [text[:max_chars]]

