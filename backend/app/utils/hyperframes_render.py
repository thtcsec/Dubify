"""Optional HyperFrames CLI render path for Studio HTML scenes (spike / Phase B)."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

def _timeline_snippet(duration: float) -> str:
    dur = max(0.5, float(duration))
    return f"""
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script>
  (function () {{
    const id = "dubify-scene";
    const duration = {dur};
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    tl.set({{}}, {{}}, duration);
    window.__timelines[id] = tl;
  }})();
</script>
"""


def node_available(*, min_major: int = 22) -> bool:
    node = shutil.which("node")
    if not node:
        return False
    try:
        out = subprocess.run(
            [node, "-v"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        match = re.match(r"v(\d+)", (out.stdout or out.stderr or "").strip())
        if not match:
            return False
        return int(match.group(1)) >= min_major
    except Exception:
        return False


def wrap_scene_as_composition(
    scene_html: str,
    *,
    width: int,
    height: int,
    duration: float = 2.0,
) -> str:
    """Wrap a studio scene body in HyperFrames composition root + timeline extent."""
    body_match = re.search(r"<body[^>]*>(.*)</body>", scene_html, re.DOTALL | re.IGNORECASE)
    inner = body_match.group(1).strip() if body_match else scene_html
    head_match = re.search(r"<head[^>]*>(.*?)</head>", scene_html, re.DOTALL | re.IGNORECASE)
    head_inner = head_match.group(1) if head_match else ""

    social_css = """
.social-overlay.tiktok-follow{position:absolute;left:48px;bottom:120px;z-index:20;display:flex;align-items:center;gap:16px;
  padding:14px 20px;border-radius:999px;background:rgba(0,0,0,.72);border:1px solid rgba(255,255,255,.2);
  animation:overlayIn .7s cubic-bezier(.22,1,.36,1) .6s both}
.tt-avatar,.tt-avatar-fallback{width:56px;height:56px;border-radius:50%;object-fit:cover;border:2px solid #fff}
.tt-avatar-fallback{background:linear-gradient(135deg,#38bdf8,#a78bfa)}
.tt-meta{display:flex;flex-direction:column;gap:6px}
.tt-handle{font-size:26px;font-weight:800;color:#fff}
.tt-follow-btn{align-self:flex-start;padding:6px 18px;border-radius:8px;background:#fe2c55;color:#fff;font-weight:700;font-size:18px}
.social-overlay.yt-lower-third{position:absolute;left:48px;bottom:72px;z-index:20;display:flex;align-items:center;gap:18px;
  padding:16px 22px;border-radius:12px;background:linear-gradient(90deg,rgba(204,0,0,.92),rgba(180,0,0,.75));
  animation:overlayIn .8s cubic-bezier(.22,1,.36,1) .5s both;max-width:88%}
.yt-avatar,.yt-avatar-fallback{width:64px;height:64px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,.9)}
.yt-avatar-fallback{background:#111}
.yt-text{display:flex;flex-direction:column;gap:4px;flex:1;min-width:0}
.yt-channel{font-size:28px;font-weight:800;color:#fff}
.yt-subline{font-size:20px;color:rgba(255,255,255,.88)}
.yt-subscribe{padding:10px 22px;border-radius:4px;background:#fff;color:#c00;font-weight:800;font-size:18px;white-space:nowrap}
@keyframes overlayIn{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.caption-pill .pill-inner{background:rgba(0,0,0,.55);border-radius:999px;padding:28px 36px;border:2px solid rgba(255,255,255,.25);
  box-shadow:0 20px 50px rgba(0,0,0,.45)}
.caption-pill .hook{font-size:inherit;font-weight:800}
@keyframes titlePop{from{opacity:0;transform:translateY(32px)}to{opacity:1;transform:translateY(0)}}
@keyframes cardPop{from{opacity:0;transform:translateY(56px) scale(.94)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes kenBurns{from{transform:scale(1.02)}to{transform:scale(1.09)}}
"""

    timeline = _timeline_snippet(duration)
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"/>
<style>{social_css}</style>
{head_inner}
</head>
<body>
<div id="stage" data-composition-id="dubify-scene" data-start="0" data-width="{width}" data-height="{height}">
{inner}
</div>
{timeline}
</body>
</html>
"""


def render_scene_png_via_hyperframes(
    html_path: Path,
    output_png: Path,
    *,
    width: int,
    height: int,
    capture_at: float = 1.25,
    duration: float = 2.0,
    timeout_s: int = 240,
) -> bool:
    """
    Render studio scene through HyperFrames CLI → short MP4 → extract PNG frame.
    Falls back silently when Node/HyperFrames/FFmpeg unavailable.
    """
    if not node_available():
        logger.info("HyperFrames skip: Node.js 22+ not found")
        return False
    if not shutil.which("ffmpeg"):
        logger.info("HyperFrames skip: ffmpeg not found")
        return False

    try:
        raw = html_path.read_text(encoding="utf-8")
        wrapped = wrap_scene_as_composition(raw, width=width, height=height, duration=duration)
        work = output_png.parent / "hf_work"
        work.mkdir(parents=True, exist_ok=True)
        # HyperFrames expects a composition folder with index.html
        comp_path = work / "index.html"
        comp_path.write_text(wrapped, encoding="utf-8")
        mp4_path = work / "scene.mp4"

        cmd = [
            "npx",
            "--yes",
            "hyperframes@latest",
            "render",
            "-c",
            str(work),
            "-o",
            str(mp4_path),
            "--fps",
            "24",
            "--quiet",
        ]
        logger.info("HyperFrames render: %s", " ".join(cmd[:6]))
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(work),
            shell=sys.platform == "win32",
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[:800]
            logger.debug("HyperFrames render failed (%s), using Playwright: %s", proc.returncode, err.strip()[:200])
            return False
        if not mp4_path.exists() or mp4_path.stat().st_size < 1000:
            logger.warning("HyperFrames output missing or too small")
            return False

        ss = max(0.1, min(capture_at, duration - 0.05))
        ff = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ss:.3f}",
                "-i",
                str(mp4_path),
                "-vframes",
                "1",
                str(output_png),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if ff.returncode != 0:
            logger.warning("HyperFrames frame extract failed: %s", (ff.stderr or "")[:400])
            return False
        ok = output_png.exists() and output_png.stat().st_size > 8_000
        if ok:
            logger.info("HyperFrames scene PNG: %s", output_png.name)
        return ok
    except subprocess.TimeoutExpired:
        logger.warning("HyperFrames render timed out")
        return False
    except Exception as exc:
        logger.warning("HyperFrames render error: %s", exc)
        return False
