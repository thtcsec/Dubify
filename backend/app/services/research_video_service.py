"""Beta: topic → research brief → Studio script with sources."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from typing import Any, Callable
from urllib.parse import quote

import requests

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.scene_image_service import fetch_wikipedia_bundle
from app.utils.script_lang import lang_instruction, spoken_content_looks_wrong_lang
from app.utils.studio_script_format import (
    clean_llm_studio_output,
    normalize_studio_script_structure,
    script_needs_format_pass,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str, dict[str, Any] | None], None]

RESEARCH_TARGET_SECONDS = 45
RESEARCH_MIN_WORDS = 110

_RESEARCH_SYSTEM = """You are a fact-conscious short-video researcher and scriptwriter.

Given a TOPIC and RECENT NEWS/WEB RESULTS, produce a JSON object ONLY (no markdown fences) with this shape:
{
  "research_summary": "2-3 sentences on what you found — focus on LATEST developments",
  "confidence": "high|medium|low",
  "sources": [
    {"title": "...", "url": "https://...", "snippet": "one line"}
  ],
  "script": "multi-line studio script in {lang}"
}

LANGUAGE: {lang_instruction}

CRITICAL RULES:
- PRIORITIZE recent news, announcements, and current events from the search results.
- Do NOT just explain what the topic IS (like a Wikipedia article). Focus on what's HAPPENING NOW.
- Include specific dates, product launches, controversies, or breaking developments.
- If search results mention recent events (last 7 days), those MUST be the focus of the script.
- Name real people, companies, products, and quote real numbers from the sources.

SCRIPT FORMAT (strict — in the JSON string use \\n for new lines):
[Hook]
3-4 short spoken sentences (~25-35 words for this section).
[STAT: number — short label]
One sentence expanding the stat.
[DEF: term — one-line explanation]
2 spoken sentences.
[Cảnh 2]
3-4 sentences with concrete detail from recent news.
[STAT: another number — label]
2 sentences.
[Cảnh 3]
2-3 sentences closing with a takeaway.
[STAT: optional third stat]

Rules:
- Total spoken words in script: 130-180 (~45-60s voiceover). Not a tiny outline.
- CONTENT: name specific products, announcements, demos, controversies, or headlines people remember.
- Include at least 2 concrete highlights from the news search results.
- Ban filler lines like "đây là nơi chia sẻ kiến thức" without a fact attached.
- sources: 3-5 items; include the actual URLs from search results.
- [STAT:] and [DEF:] on their own lines; never use them as scene headers.
- Spoken lines only (no "Welcome to our video").
- If uncertain, confidence=low and say so in research_summary.
- Output ONLY valid JSON."""


_VERIFY_SYSTEM = """You fact-check a short video script against REFERENCE NOTES.

Return JSON ONLY:
{
  "ok": true,
  "issues": ["list unclear or wrong claims, empty if ok"],
  "confidence": "high|medium|low"
}

Flag only clear contradictions with the reference or obviously outdated numbers.
Do not nitpick style."""


def _fetch_wikipedia_snippet(topic: str, lang: str = "en") -> str:
    bundle = fetch_wikipedia_bundle(topic, lang)
    if not bundle.get("extract"):
        return ""
    wiki_lang = "vi" if lang.startswith("vi") else "en"
    return (
        f"Wikipedia ({wiki_lang}): {bundle['extract']}\n"
        f"URL: {bundle.get('page_url', '')}"
    )


def _escape_json_control_chars(text: str) -> str:
    """Escape raw newlines/tabs inside JSON string literals (common LLM mistake)."""
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if ch == "\\" and in_string:
            out.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        if in_string and ord(ch) < 32:
            if ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(f"\\u{ord(ch):04x}")
            continue
        out.append(ch)
    return "".join(out)


def _parse_research_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    candidates: list[str] = [text]
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidates.append(match.group(0))

    last_err: json.JSONDecodeError | None = None
    for candidate in candidates:
        for payload in (candidate, _escape_json_control_chars(candidate)):
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                last_err = exc
                continue

    if last_err is not None:
        raise ValueError(f"AI did not return valid JSON for research: {last_err}") from last_err
    raise ValueError("AI did not return valid JSON for research.")


def _spoken_word_count(script: str) -> int:
    from app.utils.studio_script_format import strip_popup_markers_for_tts

    return len(strip_popup_markers_for_tts(script).split())


def _call_llm_json(system: str, user: str, lang: str) -> dict[str, Any]:
    provider, api_key, model = LLMService._resolve_provider_and_model()
    if provider == "ollama":
        raw = LLMService._try_ollama_rewrite(user, lang, system_hint=system)
        if not raw:
            raise ValueError("Ollama không trả về kết quả.")
    elif provider == "none" or not api_key:
        raise ValueError("Chưa cấu hình API key LLM.")
    else:
        if provider == "groq":
            raw = LLMService._call_groq(api_key, system, user, model=model)
        elif provider == "openai":
            raw = LLMService._call_openai(api_key, system, user, model=model)
        elif provider == "gemini":
            raw = LLMService._call_gemini(api_key, system, user, model=model)
        elif provider == "anthropic":
            raw = LLMService._call_anthropic(api_key, system, user, model=model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    return _parse_research_json(raw)


def _call_llm_raw(system: str, user: str, lang: str) -> str:
    provider, api_key, model = LLMService._resolve_provider_and_model()
    if provider == "ollama":
        raw = LLMService._try_ollama_rewrite(user, lang, system_hint=system)
        if not raw:
            raise ValueError("Ollama không trả về kết quả.")
        return raw
    if provider == "none" or not api_key:
        raise ValueError("Chưa cấu hình API key LLM.")
    if provider == "groq":
        return LLMService._call_groq(api_key, system, user, model=model)
    if provider == "openai":
        return LLMService._call_openai(api_key, system, user, model=model)
    if provider == "gemini":
        return LLMService._call_gemini(api_key, system, user, model=model)
    if provider == "anthropic":
        return LLMService._call_anthropic(api_key, system, user, model=model)
    raise ValueError(f"Unsupported provider: {provider}")


def _verify_script(script: str, reference: str, lang: str) -> dict[str, Any]:
    user = f"REFERENCE:\n{reference[:2500]}\n\nSCRIPT:\n{script[:3500]}"
    try:
        return _call_llm_json(_VERIFY_SYSTEM, user, lang)
    except Exception as exc:
        logger.warning("Fact-check skipped: %s", exc)
        return {"ok": True, "issues": [], "confidence": "medium"}


def _polish_script(draft: str, subject: str, lang: str) -> str:
    from app.services.script_service import ScriptService

    notes = (
        f"{lang_instruction(lang)}\n"
        f"Topic: {subject}\n"
        f"Target length: {RESEARCH_MIN_WORDS}-180 spoken words (~45-60 second short).\n"
        "Must include memorable specifics: product names, keynote moments, real numbers — not vague summaries.\n\n"
        f"Draft:\n{draft}"
    )
    return normalize_studio_script_structure(ScriptService.rewrite_studio_script(notes, lang))


def _ensure_script_language(script: str, subject: str, lang: str) -> str:
    """Re-rewrite when LLM returned English but user chose Vietnamese TTS."""
    if not spoken_content_looks_wrong_lang(script, lang):
        return script
    from app.services.script_service import ScriptService

    logger.warning("Script language mismatch for %s — rewriting in %s", subject[:40], lang)
    fix_notes = (
        f"{lang_instruction(lang)}\n"
        f"Topic: {subject}\n\n"
        "Translate and rewrite the ENTIRE script below into the target language. "
        "Keep [Hook], [Cảnh N], [STAT:], [DEF:] markers.\n\n"
        f"{script}"
    )
    try:
        return normalize_studio_script_structure(ScriptService.rewrite_studio_script(fix_notes, lang))
    except Exception as exc:
        logger.warning("Language fix skipped: %s", exc)
        return script


class ResearchVideoService:
    @staticmethod
    def research_topic_iter(
        topic: str,
        target_lang: str = "vi",
        on_progress: ProgressCallback | None = None,
    ) -> Iterator[dict[str, Any]]:
        def emit(phase: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
            if on_progress:
                on_progress(phase, message, extra)
            return {"phase": phase, "message": message, **(extra or {})}

        subject = (topic or "").strip()
        if len(subject) < 3:
            raise ValueError("Topic is too short.")
        if len(subject) > 500:
            raise ValueError("Topic must be under 500 characters.")

        lang = target_lang or "vi"
        target_seconds = int(settings.RESEARCH_VIDEO_TARGET_SECONDS or RESEARCH_TARGET_SECONDS)

        yield emit("wikipedia", "Đang mở Wikipedia…")
        wiki_bundle = fetch_wikipedia_bundle(subject, lang)
        wiki_text = _fetch_wikipedia_snippet(subject, lang)
        if wiki_bundle.get("page_url"):
            yield emit(
                "wikipedia",
                f"Đã đọc Wikipedia: {wiki_bundle.get('title', subject)}",
                {"url": wiki_bundle.get("page_url")},
            )
        else:
            yield emit("wikipedia", "Không tìm thấy bài Wikipedia — dùng LLM.")

        # ─── Web Search: find recent news and articles ───────────────────
        yield emit("web_search", "Đang tìm kiếm tin tức mới nhất…")
        web_search_text = ""
        web_sources: list[dict[str, str]] = []
        try:
            from app.services.web_search_service import WebSearchService
            searcher = WebSearchService()
            if searcher.is_available():
                # Search for recent news (last 7 days)
                news_results = searcher.search_news(subject, max_results=5, days_back=7)
                # Also do a general web search for broader context
                web_results = searcher.search(subject, max_results=4, search_type="web")
                all_results = news_results + web_results

                if all_results:
                    search_snippets = []
                    for i, r in enumerate(all_results[:8]):
                        date_str = f" ({r.published_date})" if r.published_date else ""
                        search_snippets.append(
                            f"{i+1}. [{r.source}]{date_str} {r.title}: {r.snippet}"
                        )
                        web_sources.append({
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet[:160],
                        })
                    web_search_text = "RECENT NEWS & WEB RESULTS:\n" + "\n".join(search_snippets)
                    yield emit(
                        "web_search",
                        f"Tìm thấy {len(all_results)} kết quả tin tức/web mới nhất.",
                        {"count": len(all_results)},
                    )
                else:
                    yield emit("web_search", "Không tìm thấy tin tức mới — dùng Wikipedia + LLM.")
            else:
                yield emit("web_search", "Web search chưa cấu hình — dùng Wikipedia + LLM.")
        except Exception as search_err:
            logger.warning("Web search failed: %s", search_err)
            yield emit("web_search", "Web search lỗi — tiếp tục với Wikipedia.")

        yield emit("drafting", "AI đang viết kịch bản & tổng hợp nguồn…")
        user_prompt = (
            f"TOPIC: {subject}\n"
            f"TARGET VOICEOVER: ~{target_seconds} seconds ({RESEARCH_MIN_WORDS}+ spoken words).\n"
            f"LANGUAGE: {lang_instruction(lang)}\n\n"
        )
        if web_search_text:
            user_prompt += f"{web_search_text}\n\n"
        if wiki_text:
            user_prompt += f"WIKIPEDIA CONTEXT:\n{wiki_text}\n\n"
        user_prompt += (
            "IMPORTANT: Prioritize RECENT NEWS and current events from the search results above. "
            "Do NOT just explain what the topic IS — focus on what's HAPPENING NOW. "
            "Include specific dates, announcements, product launches, or controversies from the news.\n\n"
            "Produce the JSON research package now."
        )

        system = (
            _RESEARCH_SYSTEM.replace("{lang}", lang).replace("{lang_instruction}", lang_instruction(lang))
        )
        raw = _call_llm_raw(system, user_prompt, lang)

        yield emit("parsing", "Đang xử lý kết quả JSON…")
        data = _parse_research_json(raw)
        script = normalize_studio_script_structure(str(data.get("script") or ""))
        script = _ensure_script_language(script, subject, lang)

        if script_needs_format_pass(script) or _spoken_word_count(script) < RESEARCH_MIN_WORDS:
            yield emit("writing", "Đang viết lại kịch bản dạng cảnh + popup…")
            try:
                script = _polish_script(script, subject, lang)
            except Exception as exc:
                logger.warning("Research polish skipped: %s", exc)

        script = _ensure_script_language(script, subject, lang)

        reference = wiki_text or subject
        yield emit("verify", "Đang kiểm chứng số liệu với nguồn…")
        check = _verify_script(script, reference, lang)
        issues = check.get("issues") or []
        if issues and not check.get("ok", True):
            yield emit(
                "verify",
                f"Phát hiện {len(issues)} điểm cần xem lại — chỉnh kịch bản…",
                {"issues": issues[:5]},
            )
            try:
                fix_notes = (
                    f"Topic: {subject}\n"
                    f"Fix these fact issues while keeping format:\n"
                    + "\n".join(f"- {i}" for i in issues[:6])
                    + f"\n\nScript:\n{script}"
                )
                script = _polish_script(script + "\n\n" + fix_notes, subject, lang)
            except Exception as exc:
                logger.warning("Verify rewrite skipped: %s", exc)
        else:
            yield emit("verify", "Kiểm chứng xong — không thấy mâu thuẫn rõ.")

        if len(script) < 80:
            raise ValueError("Generated script too short — try a more specific topic.")

        sources = data.get("sources") or []
        if not isinstance(sources, list):
            sources = []
        # Add web search sources (prioritize news)
        for ws in web_sources:
            if ws.get("url") and not any(s.get("url") == ws["url"] for s in sources):
                sources.append(ws)
        if wiki_bundle.get("page_url"):
            sources.insert(
                0,
                {
                    "title": wiki_bundle.get("title") or "Wikipedia",
                    "url": wiki_bundle.get("page_url", ""),
                    "snippet": (wiki_bundle.get("extract") or "")[:160],
                },
            )

        word_count = _spoken_word_count(script)
        suggested_duration = max(
            target_seconds,
            min(60, int(round(word_count / 2.4))),
        )

        result = {
            "topic": subject,
            "research_summary": str(data.get("research_summary") or "").strip(),
            "confidence": str(check.get("confidence") or data.get("confidence") or "medium").lower(),
            "sources": [
                {
                    "title": str(s.get("title") or "Source"),
                    "url": str(s.get("url") or ""),
                    "snippet": str(s.get("snippet") or ""),
                }
                for s in sources[:8]
                if isinstance(s, dict)
            ],
            "script": script,
            "wikipedia_used": bool(wiki_bundle.get("extract")),
            "wiki_thumbnail_url": wiki_bundle.get("thumbnail_url", ""),
            "target_duration_seconds": target_seconds,
            "suggested_duration_seconds": suggested_duration,
            "word_count": word_count,
            "verification_issues": issues[:8] if isinstance(issues, list) else [],
        }
        yield {"phase": "done", "message": "Hoàn tất.", "result": result}

    @staticmethod
    def research_topic(topic: str, target_lang: str = "vi") -> dict[str, Any]:
        final: dict[str, Any] | None = None
        for event in ResearchVideoService.research_topic_iter(topic, target_lang):
            if event.get("phase") == "done":
                final = event.get("result")
        if not final:
            raise ValueError("Research produced no result.")
        return final
