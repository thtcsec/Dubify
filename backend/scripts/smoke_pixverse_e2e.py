#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.studio_video_builder import build_html_scene_video
from app.services.tts_service import TTSService
from app.services.video_service import VideoService
from app.utils.studio_background import ensure_studio_background
from services.pixverse_adapter import PixVerseAdapter


def _require_bin(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required binary: {name}")


def _ffprobe_json(path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout or "{}")


def _stream_counts(probe: dict) -> tuple[int, int]:
    streams = probe.get("streams") or []
    videos = sum(1 for s in streams if (s.get("codec_type") or "").lower() == "video")
    audios = sum(1 for s in streams if (s.get("codec_type") or "").lower() == "audio")
    return videos, audios


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true", help="Force PixVerse CLI generation (no external clips).")
    parser.add_argument("--external", action="store_true", help="Force external PixVerse clips from storage/input/pixverse_smoke.")
    args = parser.parse_args()

    _require_bin("ffmpeg")
    _require_bin("ffprobe")

    if not settings.ENABLE_PIXVERSE_PRODUCER:
        print("FAIL: ENABLE_PIXVERSE_PRODUCER=false")
        return 2

    adapter = PixVerseAdapter(
        api_key=settings.PIXVERSE_API_KEY,
        api_base=settings.PIXVERSE_API_BASE,
        timeout_seconds=settings.PIXVERSE_TIMEOUT_SECONDS,
    )
    external_dir = settings.INPUT_DIR / "pixverse_smoke"
    external_clips = sorted(external_dir.glob("*.mp4")) if external_dir.exists() else []
    use_cli = False
    use_external = False

    if args.cli and args.external:
        print("FAIL: choose only one of --cli or --external")
        return 2

    if args.external:
        if len(external_clips) < 4:
            print(f"FAIL: need 4-8 PixVerse MP4 clips in: {external_dir}")
            return 2
        use_external = True
    elif args.cli:
        if not getattr(settings, "ENABLE_PIXVERSE_CLI_PRODUCER", False):
            print("FAIL: ENABLE_PIXVERSE_CLI_PRODUCER=false")
            return 2
        use_cli = True
    else:
        if settings.PIXVERSE_API_KEY:
            balance = adapter.get_credit_balance()
            credits_total = int(balance.get("credit_monthly") or 0) + int(balance.get("credit_package") or 0)
            print(
                f"PixVerse balance: monthly={balance.get('credit_monthly')} package={balance.get('credit_package')} account_id={balance.get('account_id')}"
            )
            if credits_total > 0:
                use_external = False
                use_cli = False
            elif len(external_clips) >= 4:
                print("PixVerse Platform API credits are 0; using external PixVerse clips from folder.")
                use_external = True
            elif getattr(settings, "ENABLE_PIXVERSE_CLI_PRODUCER", False):
                use_cli = True
            else:
                print("FAIL: PixVerse Platform API credits are 0.")
                print("Hint: enable PixVerse CLI producer or put 4-8 PixVerse MP4 clips into:", external_dir)
                return 2
        else:
            if len(external_clips) >= 4:
                print("PixVerse Platform API key not set; using external PixVerse clips from folder.")
                use_external = True
            elif getattr(settings, "ENABLE_PIXVERSE_CLI_PRODUCER", False):
                use_cli = True
            else:
                print("FAIL: PixVerse is not configured (no API key, no external clips, no CLI producer).")
                print("Hint: Put 4-8 PixVerse MP4 clips into:", external_dir)
                return 2

    if use_cli:
        if (
            shutil.which("pixverse") is None
            and shutil.which("pixverse.cmd") is None
            and shutil.which("pixverse.exe") is None
            and shutil.which("pixverse.ps1") is None
            and shutil.which("npx") is None
            and shutil.which("npx.cmd") is None
            and shutil.which("npx.exe") is None
            and shutil.which("npx.ps1") is None
        ):
            print("FAIL: PixVerse CLI not found (need pixverse or npx).")
            return 2
        try:
            pixverse = (
                shutil.which("pixverse")
                or shutil.which("pixverse.cmd")
                or shutil.which("pixverse.exe")
                or shutil.which("pixverse.ps1")
            )
            npx = (
                shutil.which("npx")
                or shutil.which("npx.cmd")
                or shutil.which("npx.exe")
                or shutil.which("npx.ps1")
            )
            prefix: list[str]
            if pixverse:
                if pixverse.lower().endswith(".ps1"):
                    prefix = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", pixverse]
                else:
                    prefix = [pixverse]
            elif npx:
                if npx.lower().endswith(".ps1"):
                    prefix = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", npx, "-y", "pixverse@1.1.10"]
                else:
                    prefix = [npx, "-y", "pixverse@1.1.10"]
            else:
                print("FAIL: PixVerse CLI not found (need pixverse or npx).")
                return 2

            proc = subprocess.run(
                prefix + ["auth", "status", "--json"],
                cwd=str(settings.TEMP_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads((proc.stdout or "{}").strip() or "{}")
            if not payload.get("authenticated"):
                print("FAIL: PixVerse CLI is not logged in.")
                print("Hint: run `pixverse auth login` once before smoke.")
                return 2
        except Exception as exc:
            print("FAIL: Could not verify PixVerse CLI auth:", str(exc))
            return 2

    job_id = "smoke_pixverse_e2e"
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    bg = ensure_studio_background(job_id, "9:16", image_path=None)

    script = (
        "[Scene 1]\n"
        "vivo X300 Ultra opens as a creator-first flagship. Premium lighting, cinematic staging, and a confident launch tone.\n\n"
        "[Scene 2]\n"
        "Close-up: the circular camera ring module and lens glass reflect like a professional cinema rig. The story is all about imaging identity.\n\n"
        "[Scene 3]\n"
        "A creator films at night in the city. The workflow is fast: capture, edit, publish — built for short-form platforms.\n\n"
        "[Scene 4]\n"
        "Zoom becomes storytelling: a clean, stable telephoto moment that feels like a premium commercial shot.\n\n"
        "[Scene 5]\n"
        "Final call to action: the device hero shot returns, the campaign message lands, and the product closes strong."
    )

    scene_review = [
        {
            "scene_id": "scene_01",
            "title": "Launch hero",
            "description": "Premium hero device reveal for a creator-first flagship campaign.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: a futuristic AI smartphone on a clean stage. Action: dramatic product reveal, subtle floating UI particles. Camera movement: slow push in. Lighting and style: PixVerse V6, cinematic, premium commercial lighting, sharp focus, high detail. Context: product launch hero shot.",
        },
        {
            "scene_id": "scene_02",
            "title": "Camera close-up",
            "description": "Macro circular camera ring reveal with premium reflections and launch lighting.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: close-up of vivo X300 Ultra circular camera ring module with dual 200MP storytelling emphasis. Action: macro camera module reveal with precision highlights and glass reflections, round camera ring clearly visible. Camera movement: slow macro slide and tilt. Lighting and style: PixVerse V6, cinematic macro commercial, sharp metal texture, glossy premium look. Context: emphasize creator-grade camera identity.",
        },
        {
            "scene_id": "scene_03",
            "title": "Creator workflow",
            "description": "Creator filming in an urban night setting, capture-to-edit energy, social-first premium vibe.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: young creator filming with vivo X300 Ultra in an urban night setting. Action: switching from capture to editing mindset, confident creator energy. Camera movement: handheld cinematic drift. Lighting and style: PixVerse V6, social-first premium ad, neon city bokeh, realistic cinematic motion. Context: mobile creator workflow and content production.",
        },
        {
            "scene_id": "scene_04",
            "title": "Zoom power",
            "description": "Telephoto storytelling beat: stable zoom, premium lens feel, cinematic depth compression.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: city skyline and portrait subject captured through long-range mobile zoom. Action: smooth zoom storytelling with stable focus and premium lens feel. Camera movement: slow zoom and lateral drift. Lighting and style: PixVerse V6, cinematic telephoto look, polished ad aesthetic, realistic depth compression. Context: show pro-grade zoom and storytelling power.",
        },
        {
            "scene_id": "scene_05",
            "title": "Final CTA",
            "description": "Premium launch finale with a clear campaign call-to-action.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: vivo X300 Ultra centered with bold title card and campaign finish. Action: product rotates slightly while logo and creator message resolve on screen. Camera movement: smooth orbit and settle. Lighting and style: PixVerse V6, premium launch finale, high-contrast cinematic lighting, luxury smartphone ad. Context: final campaign-ready call to action.",
        },
    ]

    tts = TTSService(voice="en-US-JennyNeural", provider=settings.STUDIO_TTS_PROVIDER, target_lang="en")
    audio_path, sub_path = await tts.generate_studio_audio_with_subtitles(script, "en", job_id)

    out = settings.TEMP_DIR / f"{job_id}.mp4"
    ok = build_html_scene_video(
        script=script,
        image_path=bg,
        audio_path=audio_path,
        subtitle_path=sub_path,
        output_path=out,
        aspect_ratio="9:16",
        template_name="tiktok_news",
        use_scene_images=False,
        scene_review_json=json.dumps(scene_review, ensure_ascii=False),
        research_topic="vivo X300 Ultra campaign",
        pixverse_clip_paths=[str(p) for p in external_clips] if use_external else None,
    )

    if not ok or not out.exists():
        print("FAIL: build_html_scene_video returned false or no output")
        return 1

    probe = _ffprobe_json(out)
    v_count, a_count = _stream_counts(probe)
    duration = VideoService.get_duration(out)
    size = out.stat().st_size
    comment = (((probe.get("format") or {}).get("tags") or {}).get("comment") or "").strip()
    print(f"OK: {out}")
    print(f"  size={size} bytes duration={duration:.2f}s streams=video:{v_count} audio:{a_count}")
    if comment:
        print(f"  tags.comment={comment}")

    prov_path = out.with_suffix(".pixverse_provenance.json")
    if not prov_path.exists():
        print("FAIL: missing provenance sidecar:", prov_path)
        return 1

    prov = json.loads(prov_path.read_text(encoding="utf-8") or "{}")
    provider = str(prov.get("provider") or "")
    shots = prov.get("shots") or []
    api_shots = [s for s in shots if str(s.get("source")) == "pixverse_api"]
    external_shots = [s for s in shots if str(s.get("source")) == "pixverse_external"]
    cli_shots = [s for s in shots if str(s.get("source")) == "pixverse_cli"]
    if provider == "pixverse":
        if len(api_shots) < 1:
            print(f"FAIL: not a real PixVerse API run (provider={provider}, api_shots={len(api_shots)})")
            return 1
    elif provider == "pixverse_external":
        if len(external_shots) < 4:
            print(f"FAIL: not enough external PixVerse clips (provider={provider}, external_shots={len(external_shots)})")
            return 1
    elif provider == "pixverse_cli":
        if len(cli_shots) < 4:
            print(f"FAIL: not enough PixVerse CLI clips (provider={provider}, cli_shots={len(cli_shots)})")
            return 1
    else:
        print(f"FAIL: PixVerse producer not used (provider={provider})")
        return 1

    if v_count < 1:
        print("FAIL: output has no video stream")
        return 1
    if a_count < 1:
        print("FAIL: output has no audio stream (voiceover missing)")
        return 1
    if duration < 25.0:
        print("FAIL: duration too short (<25s)")
        return 1
    if size < 250_000:
        print("FAIL: output too small (likely broken)")
        return 1

    print("PASS: PixVerse video + voiceover verified (provenance + ffprobe).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
