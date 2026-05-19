# Inspired open-source projects

Dubify borrows **patterns and algorithms**, not full vendored copies. Credits:

| Repo | Use in Dubify |
|------|----------------|
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Studio: `tiktok_news_pill`, social overlays, optional `hyperframes render` — [HYPERFRAMES.md](./HYPERFRAMES.md) |
| [debpalash/OmniVoice-Studio](https://github.com/debpalash/OmniVoice-Studio) | All-in-one local dub app; compare [OMNIVOICE_VS_VIBEVOICE.md](./OMNIVOICE_VS_VIBEVOICE.md) |
| [microsoft/VibeVoice](https://github.com/microsoft/VibeVoice) | Roadmap: long-form ASR + diarization (ASR-7B) |
| [Augani/openreel-video](https://github.com/Augani/openreel-video) | Studio Editor layout: project bin, transport, multi-track timeline, cue inspector |
| [OpenCut-app/OpenCut](https://github.com/OpenCut-app/OpenCut) | CapCut alternative (51k★): timeline patterns, GPU compositor (wgpu/WASM), plugin architecture, headless batch rendering |
| [AutoDubbing](https://github.com/andrewlevada/autodub) (concept) | ASR segment merge by sentence / pause |
| [Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) | `script_split.py`, HTML scene cards (`templates/studio/`), Playwright render |
| [jianchang512/pyvideotrans](https://github.com/jianchang512/pyvideotrans) | Multi-provider TTS/ASR/translation patterns, retry logic, audio preprocessing |
| [supertone-inc/supertonic](https://github.com/supertone-inc/supertonic) | Lightning-fast on-device TTS (99M params, 31 langs, Vietnamese, expression tags, ONNX) |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | Future: visual scene cuts for clip boundaries |
| [FFmpeg](https://ffmpeg.org/) | Burn subtitles, clip export, 9:16 crop, audio sync, film grain, vignette |
| [edge-tts](https://github.com/rany2/edge-tts) | Hybrid/online neural TTS |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local ASR |

## Clip export vs Auto Shorts vs Studio

| Flow | Input | Output |
|------|--------|--------|
| **Studio** | Script + layout preview (gradient bg) | TTS + HTML scene cards → MP4 |
| **AI Research Video (Beta)** | Topic → research → script | Planned — [AI_RESEARCH_VIDEO_BETA.md](./AI_RESEARCH_VIDEO_BETA.md) |
| **Auto Shorts** | Long video URL/file | Full dub → auto-cut Part 1, 2… (vertical) |
| **Studio Editor → Clip export** | Finished dub job | Manual/platform clips (FFmpeg) |

Do not merge Shorts (repurpose) with Studio (script-to-video) in one UI step.

## HyperFrames deep dive

Full notes, phase roadmap, and catalog mapping: **[docs/HYPERFRAMES.md](./HYPERFRAMES.md)**.
