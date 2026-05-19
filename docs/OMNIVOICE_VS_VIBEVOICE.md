# OmniVoice Studio vs Microsoft VibeVoice — so sánh cho Dubify

| | [OmniVoice Studio](https://github.com/debpalash/OmniVoice-Studio) | [Microsoft VibeVoice](https://github.com/microsoft/VibeVoice) |
|---|---------------------------------------------------------------------|----------------------------------------------------------------|
| **Định vị** | App desktop/web **all-in-one** thay ElevenLabs (clone, dub, dictation) | **Nghiên cứu** voice AI: ASR dài + TTS (một số model đã gỡ) |
| **License** | FSL → Apache 2.0 sau 2 năm; thương mại cần license riêng | MIT (model cards); TTS repo code đã **gỡ** khỏi GitHub (2025-09) |
| **TTS** | OmniVoice engine + CosyVoice, VoxCPM, MLX… **646 ngôn ngữ** | VibeVoice-TTS 1.5B (HF weights, code disabled), Realtime 0.5B streaming |
| **ASR** | WhisperX word-level | **VibeVoice-ASR 7B**: 60 phút/pass, diarization + timestamp + hotwords |
| **Dubbing** | Pipeline đầy đủ trong app (transcribe → translate → TTS → mux) | Không phải sản phẩm dub end-to-end; từng model riêng |
| **UI** | Tauri desktop + React, batch queue, MCP | Playground / Colab / Transformers API |
| **VRAM** | ~4 GB min, auto offload | ASR 7B nặng; Realtime 0.5B nhẹ hơn |
| **Điểm mạnh** | Trải nghiệm người dùng, đa engine, local privacy | ASR dài + structured output (Who/When/What), chất lượng research |
| **Điểm yếu** | Beta, FSL thương mại, stack nặng (~2.4 GB models) | TTS không còn trong repo chính; không app dub hoàn chỉnh |

## Cái nào “xịn” hơn?

**Không có một ông thắng tuyệt đối** — khác mục tiêu:

### Chọn **OmniVoice Studio** nếu bạn muốn:
- Tool **giống ElevenLabs** chạy local: clone giọng, design voice, **dub video** một chỗ.
- **646 ngôn ngữ TTS**, batch nhiều video, Demucs tách vocal, dictation OS-wide.
- Fork/extend backend Python (`TTSBackend` ~50 dòng) cho product riêng.

### Chọn **VibeVoice** nếu bạn muốn:
- **ASR podcast / họp dài** (tới ~60 phút), speaker + timestamp + hotword trong **một pass**.
- Tích hợp qua **Hugging Face Transformers** / vLLM trong pipeline tự build.
- **Realtime TTS** (~300 ms latency) với model 0.5B (Colab/demo).

### Cho **Dubify** cụ thể:

| Thành phần Dubify | Gợi ý |
|-------------------|--------|
| ASR (Whisper) | Giữ faster-whisper; **roadmap**: thử **VibeVoice-ASR** cho video >30 phút + diarization |
| TTS (edge-tts hybrid) | Giữ edge + Piper; OmniVoice **không** plug-and-play (engine riêng, FSL) |
| Dub pipeline | Học **flow** OmniVoice (scene split, stem export), không fork cả app |
| Shorts / clip | PySceneDetect + clip service; VibeVoice ASR giúp **boundary** theo speaker |

**Kết luận ngắn:**  
- **“Xịn” làm app dub all-in-one local:** **OmniVoice Studio** (trọn gói, UX, đa ngôn ngữ TTS).  
- **“Xịn” về ASR dài + research / speaker structure:** **VibeVoice-ASR**.  
- Dubify hiện **cân bằng tốt** với Whisper + edge-tts + FFmpeg; nâng cấp ASR nên ưu tiên **VibeVoice-ASR**, còn TTS đa ngôn ngữ offline có thể tham khảo **engine adapter** của OmniVoice sau.

## Tích hợp roadmap Dubify

1. **Phase 1:** Doc + env flag `ASR_ENGINE=whisper|vibevoice` (optional, cần GPU 8GB+ cho 7B).
2. **Phase 2:** Gọi VibeVoice-ASR qua subprocess/Docker cho job dub dài; map output → cues + speaker labels cho `ClipService`.
3. **Phase 3:** Đánh giá OmniVoice TTS qua API local (port 3900) như optional backend — không merge codebase.

## Link

- OmniVoice: https://github.com/debpalash/OmniVoice-Studio  
- VibeVoice: https://github.com/microsoft/VibeVoice  
- VibeVoice ASR Playground: https://aka.ms/vibevoice-asr  
