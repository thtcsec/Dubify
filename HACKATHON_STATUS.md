# Dubify AI Hackathon Status

## Current Capabilities

- FastAPI + React app for video dubbing from upload or URL.
- Script-to-video Studio flow with branded layout preview, social overlays, subtitles, and FFmpeg export.
- AI Research Video beta flow: topic -> research -> editable script -> render.
- Scene-based HTML rendering path using Playwright / HyperFrames-style motion and FFmpeg assembly.
- Studio editor for subtitle timing cleanup, re-burn, and clip export from completed jobs.
- Multi-provider stack already wired for ASR, translation, TTS, scene images, and optional web research.

## Missing Features

- No real PixVerse integration yet; current repo is Pixelle-style / HTML-scene based, not PixVerse-native.
- No explicit scene review approval gate between script generation and final render.
- No asset review queue to approve or replace per-scene images before export.
- No polished "submission mode" demo script or one-click guided flow across Topic -> Research -> Review -> Export.
- No automated release checklist enforcement for secrets, ignored artifacts, and demo-ready outputs.
- No clear fallback UX when research confidence is low or scene image lookup fails.

## Risks

- Root `.env` contains live-looking API credentials; they are ignored but must be rotated before demo packaging or screen sharing.
- Local workspace is noisy with many temp renders, outputs, model files, logs, and media artifacts, which increases release risk.
- Current changes are still uncommitted and mixed across docs, backend, frontend, tests, and local artifacts.
- Research quality depends on external APIs and source freshness; failures can hurt demo reliability.
- Render pipeline depends on FFmpeg plus Playwright / browser availability, which can fail on new machines.
- Large local runtime state can make the repository feel unstable or harder to hand off to judges.

## Recommended Demo Flow

1. Start from Research Video.
2. Enter a timely tech topic with clear public news coverage.
3. Run research and show sources plus confidence.
4. Review and lightly edit the generated script.
5. Open project preview and show scene/layout controls.
6. Select voice, aspect ratio, and render engine.
7. Render the video and show job progress.
8. Open the Studio editor to trim or polish subtitles.
9. Export the final MP4 and short clips.

## Submission Checklist

- Rotate all exposed local API keys and confirm no secrets are present in tracked files.
- Confirm `.gitignore` covers temp renders, logs, outputs, caches, local env files, and model downloads.
- Keep the branch for submission work isolated from `main`.
- Commit product changes in logical groups with clear `feat`, `fix`, `docs`, and `chore` messages.
- Validate the core demo path on a clean machine or clean shell session.
- Pre-generate one backup demo asset in case live render fails.
- Prepare a short spoken demo track and submission summary.
- Record evidence of TRAE usage during repo preparation and implementation.
- Clearly explain what is already working vs. what is beta.
