"""Batch/Headless Renderer — CLI interface for rendering multiple videos without UI.

Requirement 18: Process JSON manifest of rendering jobs via command line.

Usage:
    python -m app.cli.batch_render manifest.json --parallel 2 --output results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.core.logging import DubifyLogger

logger = logging.getLogger(__name__)


def _setup_logging():
    DubifyLogger.setup(level="INFO")


def _validate_manifest(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate and extract jobs from manifest."""
    jobs = manifest.get("jobs", [])
    if not jobs:
        raise ValueError("Manifest contains no jobs.")

    validated = []
    for i, job in enumerate(jobs):
        if not job.get("script") and not job.get("text"):
            logger.warning("Job %d has no script/text, skipping.", i)
            continue
        validated.append({
            "id": job.get("id", f"batch_{uuid.uuid4().hex[:8]}"),
            "script": job.get("script") or job.get("text", ""),
            "target_lang": job.get("target_lang", "vi"),
            "voice_id": job.get("voice_id", "vi-VN-HoaiMyNeural"),
            "aspect_ratio": job.get("aspect_ratio", "9:16"),
            "template": job.get("template", "tiktok_news"),
            "output_path": job.get("output_path", ""),
            "use_raw_script": job.get("use_raw_script", False),
        })

    return validated


async def _process_single_job(job: Dict[str, Any], job_index: int, total: int) -> Dict[str, Any]:
    """Process a single batch job through the Studio pipeline."""
    job_id = job["id"]
    start_time = time.time()
    logger.info("[%d/%d] Processing job: %s", job_index + 1, total, job_id)

    try:
        from app.services.script_service import ScriptService
        from app.services.tts_service import TTSService
        from app.services.studio_video_builder import build_html_scene_video
        from app.services.video_service import VideoService
        from app.utils.studio_background import ensure_studio_background

        # Step 1: Resolve script
        script = ScriptService.resolve_studio_script(
            job["script"],
            job["target_lang"],
            use_raw_script=job["use_raw_script"],
        )

        # Step 2: Generate background
        bg_path = ensure_studio_background(job_id, job["aspect_ratio"])

        # Step 3: TTS
        tts = TTSService(voice=job["voice_id"], target_lang=job["target_lang"])
        audio_path, srt_path = await tts.generate_studio_audio_with_subtitles(
            script, job["target_lang"], job_id
        )

        # Step 4: Render video
        output_path = Path(job["output_path"]) if job["output_path"] else (
            settings.OUTPUT_DIR / f"{job_id}_batch.mp4"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        success = build_html_scene_video(
            script=script,
            image_path=bg_path,
            audio_path=audio_path,
            subtitle_path=srt_path,
            output_path=output_path,
            aspect_ratio=job["aspect_ratio"],
            template_name=job["template"],
        )

        if not success:
            # Fallback to classic render
            success = VideoService.image_audio_to_video(
                image_path=bg_path,
                audio_path=audio_path,
                output_path=output_path,
                srt_path=srt_path,
                aspect_ratio=job["aspect_ratio"],
            )

        elapsed = time.time() - start_time
        if success and output_path.exists():
            logger.info("[%d/%d] ✓ Job %s completed in %.1fs → %s", job_index + 1, total, job_id, elapsed, output_path)
            return {
                "id": job_id,
                "status": "success",
                "output_path": str(output_path),
                "duration_seconds": round(elapsed, 1),
            }
        else:
            return {
                "id": job_id,
                "status": "failed",
                "error": "Render produced no output.",
                "duration_seconds": round(elapsed, 1),
            }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("[%d/%d] ✗ Job %s failed: %s", job_index + 1, total, job_id, e)
        return {
            "id": job_id,
            "status": "failed",
            "error": str(e),
            "duration_seconds": round(elapsed, 1),
        }


async def _run_batch(jobs: List[Dict[str, Any]], parallel: int) -> List[Dict[str, Any]]:
    """Run batch jobs with concurrency control."""
    semaphore = asyncio.Semaphore(parallel)
    results: List[Dict[str, Any]] = []

    async def _bounded(job, idx):
        async with semaphore:
            return await _process_single_job(job, idx, len(jobs))

    tasks = [_bounded(job, i) for i, job in enumerate(jobs)]
    results = await asyncio.gather(*tasks)
    return list(results)


def main():
    parser = argparse.ArgumentParser(description="Dubify Batch Renderer — headless video production")
    parser.add_argument("manifest", help="Path to JSON manifest file")
    parser.add_argument("--parallel", type=int, default=1, help="Max concurrent jobs (default: 1)")
    parser.add_argument("--output", default="batch_results.json", help="Output results JSON path")
    args = parser.parse_args()

    _setup_logging()

    # Load manifest
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    jobs = _validate_manifest(manifest)
    if not jobs:
        print("Error: No valid jobs in manifest.")
        sys.exit(1)

    print(f"Dubify Batch Renderer — {len(jobs)} jobs, parallel={args.parallel}")
    print("=" * 60)

    # Set Windows event loop policy
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Run
    start = time.time()
    results = asyncio.run(_run_batch(jobs, args.parallel))
    total_time = time.time() - start

    # Write results
    output = {
        "total_jobs": len(jobs),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "total_time_seconds": round(total_time, 1),
        "results": results,
    }

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"Done: {output['successful']}/{output['total_jobs']} succeeded in {total_time:.1f}s")
    print(f"Results: {output_path}")

    sys.exit(0 if output["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
