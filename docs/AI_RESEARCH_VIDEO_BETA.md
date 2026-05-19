# AI Research Video (Beta) — product sketch

**Status:** Planned / not implemented. Tag **Beta** in UI when shipped.

## Vision

User enters a **topic** (e.g. “Gemini 2.5 on Android”). The pipeline:

1. **Research** — web search + optional doc upload (PDF, URLs).
2. **Synthesize** — LLM drafts a scene script with citations internally.
3. **Verify** — second pass or tool calls flag low-confidence claims; optional “sources” popup.
4. **Visuals** — stock/CC images, generated stills, or user-provided assets; **copyright mode** (licensed-only vs best-effort).
5. **Motion** — HTML scene cards (existing Studio), Ken Burns, or HyperFrames-style CSS animation.
6. **Popups** — `[STAT]` / `[DEF]` / source chips (already in Dubify Studio format).
7. **Render** — TTS + Playwright/HyperFrames + FFmpeg (existing worker).

Output should feel like a **short edited explainer**, not a slideshow.

## Feasibility

| Piece | Feasibility | Notes |
|-------|-------------|--------|
| Topic → script | **High** | You already have LLM rewrite + scene headers. |
| Web research | **Medium** | Needs search API (Tavily, Brave, Serper) + fetch + chunk + cite. |
| Fact-check | **Medium–Low** | Full verification is hard; practical approach: confidence labels + source links, not “truth oracle”. |
| Auto images | **Medium** | Pexels/Unsplash APIs + alt text; **avoid** scraping random images without license. |
| Animation | **High** | Reuse `studio_html_service`, HyperFrames, templates. |
| End-to-end quality | **Medium** | MVP = 3–5 min video; polish = months. |

**Conclusion:** Khả thi như **pipeline mở rộng** trên Studio hiện tại, không cần viết lại toàn bộ app. Không nên “xây từ đầu” trừ module research/rights.

## Build vs borrow

| Approach | Recommendation |
|----------|----------------|
| **From scratch** | Orchestration layer only (job steps, UI, prompts). |
| **Learn / integrate** | HyperFrames (motion HTML), Remotion (if you want React timelines), Pixelle-Video patterns (already referenced), LangGraph/CrewAI for research agents (optional). |

Repos to study (also in [INSPIRED_REPOS.md](./INSPIRED_REPOS.md)):

- [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) — frame-accurate HTML video.
- [AIDC-AI/Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) — script → HTML scenes → video.
- [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) — multi-step research graphs (heavy).
- [microsoft/graphrag](https://github.com/microsoft/graphrag) — doc-heavy topics (overkill for MVP).

## Suggested MVP phases

1. **Beta v0** — Topic + single LLM call with `web_search` tool → script → existing Studio render (gradient bg).
2. **Beta v1** — Source list in popups; Pexels image per scene; user picks copyright mode.
3. **Beta v2** — Upload PDF; verification pass; scene-level asset review UI before render.

## Risks

- **Copyright** — default to licensed stock + attribution; never silently use random web images in production.
- **Hallucination** — market as “AI-assisted”, show sources, allow edit-before-render.
- **Cost/latency** — research + image + render per job; queue and cap length.

## Dubify hooks (existing)

- `POST /studio/rewrite-script`
- `studio_script_format` (`[STAT]`, `[DEF]`)
- `StudioLayoutPreview` + brand store
- `hyperframes_render.py` / Playwright pipeline

New work is mostly: **research service**, **asset resolver**, **pre-render review screen**, and a **Beta** nav entry.
