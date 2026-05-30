#!/usr/bin/env python3
from __future__ import annotations

import asyncio
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
    if not settings.PIXVERSE_API_KEY:
        if len(external_clips) >= 4:
            print("PixVerse API key not set; using external PixVerse clips from folder.")
            use_external = True
        else:
            print("FAIL: PIXVERSE_API_KEY is missing in .env")
            print(f"Hint: Put 4-8 PixVerse MP4 clips into: {external_dir}")
            return 2
    else:
        balance = adapter.get_credit_balance()
        credits_total = int(balance.get("credit_monthly") or 0) + int(balance.get("credit_package") or 0)
        print(
            f"PixVerse balance: monthly={balance.get('credit_monthly')} package={balance.get('credit_package')} account_id={balance.get('account_id')}"
        )
        use_external = credits_total <= 0 and len(external_clips) >= 4
        if credits_total <= 0 and not use_external:
            print("FAIL: PixVerse Platform API credits are 0. Cannot run real PixVerse generation.")
            print("Note: Platform API credits are separate from PixVerse Web (app.pixverse.ai) membership.")
            print(f"Hint: Put 4-8 PixVerse MP4 clips into: {external_dir}")
            return 2

    job_id = "smoke_pixverse_e2e"
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    bg = ensure_studio_background(job_id, "9:16", image_path=None)

    script = (
        "[Scene 1]\n"
        "Một chiếc điện thoại AI xuất hiện giữa ánh đèn sân khấu, màn hình hiển thị trợ lý thông minh.\n\n"
        "[Scene 2]\n"
        "Cảnh cận: giao diện gợi ý lịch trình, camera slow push in, ánh sáng cinematic.\n\n"
        "[Scene 3]\n"
        "Chuyển cảnh: người dùng ra lệnh bằng giọng nói, điện thoại phản hồi tức thì.\n\n"
        "[Scene 4]\n"
        "Biểu đồ tăng trưởng: AI phones bùng nổ năm 2026, phong cách viral social.\n\n"
        "[Scene 5]\n"
        "Kết: sản phẩm xoay 360, logo hiện lên, kêu gọi hành động rõ ràng."
    )

    scene_review = [
        {
            "scene_id": "scene_01",
            "title": "Launch hero",
            "description": "Điện thoại AI xuất hiện giữa ánh đèn sân khấu, phong cách cinematic product reveal.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: a futuristic AI smartphone on a clean stage. Action: dramatic product reveal, subtle floating UI particles. Camera movement: slow push in. Lighting and style: PixVerse V6, cinematic, premium commercial lighting, sharp focus, high detail. Context: product launch hero shot.",
        },
        {
            "scene_id": "scene_02",
            "title": "UI close-up",
            "description": "Cảnh cận giao diện trợ lý, hiển thị lịch trình và nhắc việc.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: close-up of an AI assistant UI on a smartphone screen. Action: schedule cards animate smoothly. Camera movement: slow push in with slight parallax. Lighting and style: PixVerse V6, clean tech aesthetic, soft cinematic light, high detail. Context: assistant planning scene.",
        },
        {
            "scene_id": "scene_03",
            "title": "Voice command",
            "description": "Người dùng ra lệnh bằng giọng nói, điện thoại phản hồi tức thì.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: person speaking to a smartphone, modern indoor setting. Action: voice command triggers instant assistant response, subtle UI glow. Camera movement: handheld gentle drift. Lighting and style: PixVerse V6, realistic cinematic, warm soft light, high detail. Context: real-life usage moment.",
        },
        {
            "scene_id": "scene_04",
            "title": "Market surge",
            "description": "Biểu đồ tăng trưởng và hình ảnh thị trường AI phones năm 2026.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: futuristic data visualization with rising chart and silhouettes of smartphones. Action: chart lines surge upward with dynamic motion. Camera movement: slow orbit. Lighting and style: PixVerse V6, vibrant tech commercial, high contrast, crisp details. Context: market growth beat.",
        },
        {
            "scene_id": "scene_05",
            "title": "Final CTA",
            "description": "Sản phẩm xoay 360, logo hiện lên, kết thúc mạnh.",
            "duration_seconds": 6,
            "approved": True,
            "prompt": "Subject: AI smartphone rotating 360 on a premium pedestal. Action: logo appears with subtle particles, confident finish. Camera movement: smooth orbit and settle. Lighting and style: PixVerse V6, premium commercial, glossy reflections, high detail. Context: final call-to-action end frame.",
        },
    ]

    tts = TTSService(voice="vi-VN-HoaiMyNeural", provider=settings.STUDIO_TTS_PROVIDER, target_lang="vi")
    audio_path, sub_path = await tts.generate_studio_audio_with_subtitles(script, "vi", job_id)

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
        research_topic="AI Phones 2026",
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
    if provider == "pixverse":
        if len(api_shots) < 1:
            print(f"FAIL: not a real PixVerse API run (provider={provider}, api_shots={len(api_shots)})")
            return 1
    elif provider == "pixverse_external":
        if len(external_shots) < 4:
            print(f"FAIL: not enough external PixVerse clips (provider={provider}, external_shots={len(external_shots)})")
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
