# Dubify AI Hackathon Roadmap

## Priority 1: Must Finish Before Demo

- Clean release surface: rotate local secrets, verify ignore rules, and avoid committing temp outputs or generated media.
- Split the current workspace changes into reviewable commits on `hackathon-trae-pixverse-2026`.
- Tighten the main demo flow around Topic -> Research -> Script Review -> Layout Review -> Render -> Edit -> Export.
- Add a lightweight scene review step in the UI before final render using the existing project preview.
- Prepare one demo topic, one backup topic, and one pre-rendered fallback output.
- Confirm Playwright / FFmpeg / model prerequisites are documented and reproducible.

## Priority 2: Nice To Have

- Add a simple per-scene asset review panel with keep / refresh / fallback behavior.
- Surface low-confidence research warnings more prominently before render.
- Add a hackathon-specific landing copy or sidebar label that highlights the end-to-end video generation story.
- Add a one-click "demo preset" for vertical aspect ratio, branded layout, and safe render defaults.
- Add a small release script or checklist command for pre-demo verification.

## Priority 3: Future Work

- Integrate actual PixVerse asset or shot generation instead of only Pixelle-style HTML scene rendering.
- Add richer studio timeline editing beyond subtitle adjustment and clip export.
- Support document upload, source grounding, and stronger claim verification for research videos.
- Add collaborative review states for script approval, scene approval, and final publish readiness.
- Expand template packs, transitions, motion styles, and branded export presets.
