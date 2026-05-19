# HyperFrames — học hỏi cho Dubify

Nguồn: [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (Apache 2.0) · Docs: [hyperframes.heygen.com](https://hyperframes.heygen.com/introduction) · Index LLM: [llms.txt](https://hyperframes.mintlify.app/llms.txt)

**Tóm tắt:** HyperFrames (HF) = viết **HTML thuần** + `data-*` timing → headless Chrome **seek từng frame** → FFmpeg → MP4 **deterministic**. Tối ưu cho agent (CLI không tương tác, skills, catalog 50+ block).

---

## So sánh nhanh với Dubify

| Khía cạnh | HyperFrames | Dubify hiện tại |
|-----------|-------------|-----------------|
| **Studio (kịch bản → video)** | 1 composition HTML, GSAP/CSS **seek theo frame** | Template HTML → **1 PNG/scene** (Playwright) → FFmpeg Ken Burns + xfade |
| **Dubbing / Shorts** | Có skill TTS/Whisper trong CLI media | Pipeline riêng: ASR → dịch → TTS → merge → `ClipService` cắt part |
| **Phụ đề karaoke** | Catalog: `caption-pill-karaoke`, `caption-highlight`, … | ASS karaoke (`studio_karaoke.py`) burn hoặc overlay player |
| **Chuyển cảnh** | Shader transitions, `data-start="intro - 0.5"` overlap | FFmpeg `xfade` giữa segment PNG |
| **Preview** | `npx hyperframes preview` live reload | React UI + job polling |
| **License** | Apache 2.0, không phí render | Tự host, tùy stack |

**Kết luận:** Dubify **không cần thay** toàn bộ bằng HF. Học HF để nâng **Studio HTML** (motion deterministic, caption components, social overlays) và tham khảo **media skills** (TTS/transcribe) — giữ pipeline dub/shorts Python đã ổn.

---

## Mô hình HF cần nhớ

### 1. Composition + data attributes

Root:

```html
<div id="stage"
     data-composition-id="my-video"
     data-start="0"
     data-width="1080"
     data-height="1920">
```

Clip (bắt buộc `class="clip"`):

```html
<h1 class="clip"
    data-start="2"
    data-duration="5"
    data-track-index="1">
  Tiêu đề
</h1>
```

**Relative timing** (rất hữu ích cho chuỗi cảnh):

```html
<video id="intro" class="clip" data-start="0" data-duration="10" ...></video>
<video id="main" class="clip" data-start="intro" data-duration="20" ...></video>
<video id="broll" class="clip" data-start="intro - 0.5" data-track-index="1" ...></video>
```

→ Dubify roadmap: map `[Mở đầu]` / `[Phần 2]` → `data-start` chain thay vì chỉ tính `start/end` trong Python.

### 2. Deterministic render

- `frame = floor(time * fps)` — mỗi frame seek, không phụ thuộc wall-clock.
- Animation: GSAP timeline **paused**, đăng ký `window.__timelines["my-video"]` khớp `data-composition-id`.
- **Không** gọi `video.play()` / `audio.currentTime` trong script — framework sync media.

**Gap Dubify:** CSS `@keyframes` + Playwright chụp **một** screenshot = animation “đóng băng” ở frame đầu; motion thật đang làm ở FFmpeg (`_scene_motion_filter`). HF = motion trong HTML **đúng từng giây**.

### 3. Frame Adapters

GSAP, Anime.js, Lottie, CSS WAAPI, Three.js — tất cả seek qua `hf-seek` / `window.__hf*Time`, không chạy real-time khi render.

### 4. Catalog (copy ý tưởng, không vendoring)

| HF block / component | Áp dụng Dubify |
|----------------------|----------------|
| `caption-pill-karaoke`, `caption-highlight` | Template Studio + ASS style |
| `tiktok-follow`, `yt-lower-third` | `studio_overlay.py` header/footer |
| `transitions-*`, `flash-through-white` | Thay/thêm FFmpeg xfade presets |
| `grain-overlay`, `vignette` | CSS layer trong template hoặc FFmpeg filter |
| `data-chart`, maps | Roadmap Studio “infographic” |

Cài block HF (tham khảo local): `npx hyperframes add caption-pill-karaoke` — đọc HTML snippet, port sang `backend/templates/studio/`.

### 5. Common mistakes (tránh khi port template)

1. **Không animate width/height trực tiếp trên `<video>`** — bọc `motion.div` wrapper.
2. **`class="clip"`** trên mọi phần tử có `data-start`.
3. Timeline GSAP phải dài bằng video (`tl.set({}, {}, DURATION)`).
4. Ảnh nguồn ≤ ~2× canvas (1080×1920 → max ~2160×3840).
5. Hạn chế stack `backdrop-filter: blur()` — template `tiktok_news` đã dùng 1 lớp blur card.

---

## Lộ trình tích hợp đề xuất (theo effort)

### Phase A — Không đổi stack (1–2 ngày)

- [x] Template `tiktok_news_pill.html` (pill caption, all aspects).
- [x] `backend/templates/studio/README.md` + `{SOCIAL_OVERLAY}` placeholder.
- [x] `studio_overlay.py`: TikTok follow + YouTube lower third HTML.
- [x] Spike `hyperframes_render.py` (`STUDIO_RENDER_ENGINE=auto|hyperframes|playwright`).
- [ ] Clip boundaries: thử PySceneDetect song song `ClipService` mode `scene`.

### Phase B — Seekable Studio (1–2 tuần)

- [ ] Option render: thay “1 PNG/scene” bằng **N frame/scene** (Playwright `page.evaluate` set `--hf-time` hoặc negative `animation-delay`).
- [ ] Hoặc subprocess `npx hyperframes render` cho từng scene HTML export từ `StudioHtmlService`.
- [ ] Linter nhẹ: timed element phải có duration (tương tự `hyperframes lint`).

### Phase C — Tùy chọn monorepo / dependency

- [ ] `@hyperframes/producer` trong Docker worker (Node 22 + FFmpeg) — chỉ cho Studio, giữ Python cho dub.
- [ ] Skill `hyperframes` cho Cursor khi user bảo “làm video từ kịch bản” trong repo.

**Không khuyến nghị ngay:** thay Playwright bằng Puppeteer HF engine toàn app — trùng chức năng, thêm Node runtime vào backend Python.

---

## Map package HF → file Dubify

| HF package | Dubify tương đương |
|------------|-------------------|
| `@hyperframes/core` (parse, lint) | `studio_scenes.py`, `template_fill.py` |
| `@hyperframes/engine` | `studio_playwright.py` + `studio_html_service.py` |
| `@hyperframes/producer` | `studio_video_builder.py` + `VideoService.studio_scenes_to_video` |
| `@hyperframes/studio` | `StudioView.tsx`, `StudioEditorView.tsx` |
| CLI `hyperframes-media` (TTS/Whisper) | `tts_service.py`, `asr_service.py` (đã có) |
| Skills / catalog | `docs/HYPERFRAMES.md`, template `backend/templates/studio/` |

---

## Prompt mẫu (khi dùng agent + HF song song)

```text
Dựa trên docs/HYPERFRAMES.md và template backend/templates/studio/1080x1920/tiktok_news.html,
tạo scene HTML 9:16 với hook card + karaoke pill, timing 0–8s, không dùng video.play() trong JS.
```

```text
Port ý tưởng hyperframes catalog caption-highlight vào ASS style studio_karaoke.py
(active word màu vàng, nền đỏ TikTok).
```

---

## Tài liệu đọc tiếp

1. [Compositions](https://hyperframes.mintlify.app/concepts/compositions.md)
2. [Data attributes](https://hyperframes.mintlify.app/concepts/data-attributes.md)
3. [Determinism](https://hyperframes.mintlify.app/concepts/determinism.md)
4. [GSAP Animation](https://hyperframes.mintlify.app/guides/gsap-animation.md)
5. [Common mistakes](https://hyperframes.mintlify.app/guides/common-mistakes.md)
6. [HyperFrames vs Remotion](https://hyperframes.mintlify.app/guides/hyperframes-vs-remotion.md)
7. [Pipeline 7 bước](https://hyperframes.mintlify.app/guides/pipeline.md) — so với dub 7 bước trong worker Shorts

---

## Ghi chú license

HF: **Apache 2.0** — được port pattern/snippet vào template Dubify; ghi credit trong `INSPIRED_REPOS.md`. Không copy nguyên catalog vào repo mà không kiểm tra license từng file snippet (thường cùng Apache trong repo HF).
