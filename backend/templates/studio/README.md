# Studio HTML templates

Pixelle-Video-style scene cards rendered via Playwright (`StudioHtmlService`).

## Placeholders

| Token | Mô tả |
|-------|--------|
| `{TEXT}` | Thoại / hook (đã escape HTML) |
| `{TITLE_BLOCK}` | Optional `<div class="title">…</div>` |
| `{IMAGE_URL}` | `file://` path ảnh nền |

## Aspect folders

`1080x1920` (9:16), `1080x1440`, `1920x1080`, `1440x1080`, `1080x1080`

## Học từ HyperFrames

Xem [docs/HYPERFRAMES.md](../../../docs/HYPERFRAMES.md).

**Khác biệt quan trọng:** Dubify chụp **một frame** mỗi cảnh rồi animate bằng FFmpeg. HyperFrames **seek** CSS/GSAP từng frame trong Chrome — motion mượt hơn nhưng cần timeline paused + `data-start` / `class="clip"`.

Khi port block từ [HF catalog](https://hyperframes.heygen.com/catalog):

1. Giữ kích thước canvas đúng folder.
2. Tránh stack nhiều `backdrop-filter`.
3. Resize ảnh nền ≤ 2× canvas trước render.
4. Karaoke: HTML chỉ hiển thị tiêu đề cảnh (nếu có); thoại burn bằng ASS karaoke (`burn_subtitles=True`) — từ vàng highlight theo thời gian, vị trí ~64% khung dọc.
