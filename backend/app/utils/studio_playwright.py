"""Ensure Playwright + Chromium are ready for Pixelle-style HTML scene renders."""

from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

_checked = False
_ready = False


def playwright_render_ready(*, auto_install: bool = True) -> bool:
    """Return True if Chromium can render studio HTML scenes."""
    global _checked, _ready
    if _checked:
        return _ready

    _checked = True
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if not auto_install:
            logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        logger.info("Installing Playwright package for studio HTML renders...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright>=1.49.0"], check=False)
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            logger.error("Playwright install failed.")
            return False

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        _ready = True
        return True
    except Exception as exc:
        if not auto_install:
            logger.warning("Playwright Chromium missing: %s", exc)
            return False
        logger.info("Installing Playwright Chromium browser...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                browser.close()
            _ready = True
            return True
        except Exception as retry_exc:
            logger.error("Playwright Chromium still unavailable: %s", retry_exc)
            _ready = False
            return False
