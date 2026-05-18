# Inspired open-source projects

Dubify borrows **patterns and algorithms**, not full vendored copies. Credits:

| Repo | Use in Dubify |
|------|----------------|
| [Augani/openreel-video](https://github.com/Augani/openreel-video) | Studio Editor layout: project bin, transport, multi-track timeline, cue inspector |
| [AutoDubbing](https://github.com/andrewlevada/autodub) (concept) | ASR segment merge by sentence / pause |
| [Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) | `script_split.py`, HTML scene cards (`templates/studio/`), Playwright render |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | Future: visual scene cuts for clip boundaries |
| [FFmpeg](https://ffmpeg.org/) | Burn subtitles, clip export, 9:16 crop, audio sync |
| [edge-tts](https://github.com/rany2/edge-tts) | Hybrid/online neural TTS |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local ASR |

## Clip export vs Auto Shorts

- **Studio Editor → Clip export**: slices a **finished dub** for TikTok / Shorts / Reels (FFmpeg).
- **Auto Shorts tab**: generates a **new AI video** from prompt/script (fal.ai / local render).

Do not merge these flows in the UI; they serve different jobs.
