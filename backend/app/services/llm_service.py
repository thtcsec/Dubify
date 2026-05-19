import logging
import requests
from typing import Optional
from app.core.config import settings
from app.services.llm_models import catalog_entry, parse_llm_model_id
from app.utils.studio_script_format import clean_llm_studio_output

logger = logging.getLogger(__name__)

_STUDIO_REWRITE_SYSTEM = """You are a viral short-form news scriptwriter for vertical video (TikTok/Reels).

Rewrite the user's notes into a NEW script in {lang}. Do NOT copy-paste URLs, markdown, bullet junk, or raw excerpts from the input.

FORMAT (strict):
- Use 2-4 scene lines: [Hook], [Story], [Insight], [Close] (localized titles OK).
- Under each header: 2-4 short spoken sentences.
- Mark every impressive NUMBER or percentage with [STAT: value — short label] on its own line or inline.
- Mark technical terms the audience may not know with [DEF: term — one-line explanation].
- Hook must grab attention in the first sentence. Include at least 2 [STAT: ...] markers total.
- No markdown, no stage directions, no "Here is the script".

Example snippet:
[Hook]
Android 17 changes everything.
[STAT: 2 tỷ — thiết bị Android]
[DEF: Gemini — AI điều khiển thao tác thay người dùng]

Write ONLY the script."""


class LLMService:
    """Multi-provider LLM service. Auto-selects: Groq > OpenAI > Gemini > raw fallback."""

    @staticmethod
    def _api_key_for_provider(provider: str) -> str:
        keys = {
            "groq": settings.GROQ_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
        }
        return keys.get(provider, "")

    @staticmethod
    def _get_provider() -> tuple[str, str]:
        """Return (provider_name, api_key) for the first available provider."""
        if settings.GROQ_API_KEY:
            return "groq", settings.GROQ_API_KEY
        if settings.OPENAI_API_KEY:
            return "openai", settings.OPENAI_API_KEY
        if settings.GEMINI_API_KEY:
            return "gemini", settings.GEMINI_API_KEY
        if settings.ANTHROPIC_API_KEY:
            return "anthropic", settings.ANTHROPIC_API_KEY
        return "none", ""

    @staticmethod
    def _resolve_provider_and_model() -> tuple[str, str, str]:
        """(provider, api_key, model_id) honoring settings.LLM_MODEL catalog."""
        configured = (settings.LLM_MODEL or "auto").strip()
        if configured and configured.lower() != "auto":
            provider, model = parse_llm_model_id(configured)
            if provider == "ollama":
                return "ollama", "", model or settings.OLLAMA_MODEL
            api_key = LLMService._api_key_for_provider(provider)
            if api_key:
                return provider, api_key, model
        provider, api_key = LLMService._get_provider()
        entry = catalog_entry(f"{provider}:llama-3.3-70b-versatile") if provider == "groq" else None
        default_model = entry["model"] if entry else "gpt-4o-mini"
        if provider == "openai":
            default_model = "gpt-4o-mini"
        elif provider == "gemini":
            default_model = "gemini-2.0-flash"
        elif provider == "anthropic":
            default_model = "claude-sonnet-4-20250514"
        elif provider == "groq":
            default_model = "llama-3.3-70b-versatile"
        return provider, api_key, default_model

    @staticmethod
    def llm_available() -> bool:
        provider, api_key = LLMService._get_provider()
        return provider != "none" and bool(api_key)

    @staticmethod
    def rewrite_studio_script(raw_text: str, target_lang: str = "vi") -> str:
        """Engaging scene-based script with [STAT]/[DEF] popup markers."""
        source = (raw_text or "").strip()
        if not source:
            raise ValueError("Script is empty.")

        lang = target_lang or "vi"
        system_prompt = _STUDIO_REWRITE_SYSTEM.format(lang=lang)
        provider, api_key, model = LLMService._resolve_provider_and_model()

        if provider == "ollama" or (provider == "none" and not api_key):
            ollama_out = LLMService._try_ollama_rewrite(source, lang, system_hint=system_prompt)
            if ollama_out:
                return clean_llm_studio_output(ollama_out)
            raise ValueError(
                "Không viết lại được kịch bản: cần API key (Cài đặt) hoặc Ollama tại "
                + settings.OLLAMA_API_BASE
            )

        if provider == "none" or not api_key:
            raise ValueError("Chưa cấu hình API key LLM trong Cài đặt.")

        try:
            if provider == "groq":
                out = LLMService._call_groq(api_key, system_prompt, source, model=model)
            elif provider == "openai":
                out = LLMService._call_openai(api_key, system_prompt, source, model=model)
            elif provider == "gemini":
                out = LLMService._call_gemini(api_key, system_prompt, source, model=model)
            elif provider == "anthropic":
                out = LLMService._call_anthropic(api_key, system_prompt, source, model=model)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except Exception as exc:
            logger.error("Studio rewrite failed (%s): %s", provider, exc)
            raise ValueError(f"AI rewrite failed: {exc}") from exc

        cleaned = clean_llm_studio_output(out)
        if len(cleaned) < 80:
            raise ValueError("AI trả về kịch bản quá ngắn — thử model khác trong Cài đặt.")
        if cleaned.strip() == source.strip():
            raise ValueError("AI chưa viết lại đủ — thử model mạnh hơn hoặc rút gọn input.")
        return cleaned

    @staticmethod
    def generate_news_script(raw_text: str, target_lang: str = "vi", *, studio_rewrite: bool = False) -> str:
        """
        Rewrite raw news text into an engaging, professional news script.
        studio_rewrite=True: use API keys even when PROCESSING_ENGINE=local (Studio toggle).
        """
        if not studio_rewrite and not settings.allow_cloud_llm():
            logger.info("Processing mode does not allow cloud LLM rewrite. Returning raw text.")
            return raw_text.strip()

        provider, api_key = LLMService._get_provider()

        if provider == "none":
            if studio_rewrite:
                ollama = LLMService._try_ollama_rewrite(raw_text, target_lang)
                if ollama:
                    return ollama
            logger.warning("No LLM API key found. Falling back to raw text.")
            return raw_text.strip()

        system_prompt = (
            f"You are an expert news anchor scriptwriter. Rewrite the following text into "
            f"a short, engaging, and highly professional news script spoken in language: {target_lang}. "
            f"Do not include any visual cues, stage directions, or markdown. ONLY output the spoken text."
        )

        try:
            if provider == "groq":
                return LLMService._call_groq(api_key, system_prompt, raw_text)
            elif provider == "openai":
                return LLMService._call_openai(api_key, system_prompt, raw_text)
            elif provider == "gemini":
                return LLMService._call_gemini(api_key, system_prompt, raw_text)
            elif provider == "anthropic":
                return LLMService._call_anthropic(api_key, system_prompt, raw_text)
        except Exception as e:
            logger.error(f"LLM ({provider}) failed: {e}")
            return raw_text.strip()
        return raw_text.strip()

    @staticmethod
    def _try_ollama_rewrite(
        raw_text: str,
        target_lang: str,
        *,
        system_hint: str | None = None,
    ) -> str:
        """Local Ollama fallback when no cloud key."""
        try:
            url = settings.OLLAMA_API_BASE
            hint = system_hint or (
                f"Rewrite into engaging short video script in {target_lang}. "
                "Use [Hook] headers, [STAT: number], [DEF: term]. No markdown.\n\n"
            )
            prompt = f"{hint}\n\n{raw_text.strip()}"
            payload = {"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False}
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                out = (response.json().get("response") or "").strip()
                if len(out) > 40 and out != raw_text.strip():
                    logger.info("Studio script rewritten via Ollama (%d chars).", len(out))
                    return out
        except Exception as e:
            logger.warning("Ollama script rewrite failed: %s", e)
        return ""

    @staticmethod
    def generate_short_script(prompt: str, target_lang: str = "vi") -> str:
        """
        Generate a short-form script from a prompt.
        Falls back to a template if no API key is configured.
        """
        cleaned_prompt = (prompt or "").strip()
        if not cleaned_prompt:
            return ""

        if not settings.allow_cloud_llm():
            logger.info("Processing mode does not allow cloud LLM. Using template fallback.")
            return LLMService._fallback_short_script(cleaned_prompt, target_lang)

        provider, api_key = LLMService._get_provider()

        if provider == "none":
            logger.warning("No LLM API key found. Falling back to template.")
            return LLMService._fallback_short_script(cleaned_prompt, target_lang)

        system_prompt = (
            "You are a short-form video scriptwriter."
            " Create a tight, engaging, spoken-only script for a vertical short (9:16)."
            f" Write in language: {target_lang}."
            " Keep it punchy: hook, 3 fast takeaways, close with a soft CTA."
            " No bullet points, no markdown, no stage directions."
        )

        try:
            if provider == "groq":
                return LLMService._call_groq(api_key, system_prompt, cleaned_prompt)
            if provider == "openai":
                return LLMService._call_openai(api_key, system_prompt, cleaned_prompt)
            if provider == "gemini":
                return LLMService._call_gemini(api_key, system_prompt, cleaned_prompt)
            if provider == "anthropic":
                return LLMService._call_anthropic(api_key, system_prompt, cleaned_prompt)
        except Exception as e:
            logger.error(f"LLM ({provider}) failed for shorts: {e}")
            return LLMService._fallback_short_script(cleaned_prompt, target_lang)
        return LLMService._fallback_short_script(cleaned_prompt, target_lang)

    @staticmethod
    def _fallback_short_script(prompt: str, target_lang: str) -> str:
        topic = prompt.strip()
        if target_lang.lower().startswith("vi"):
            return (
                f"Hom nay noi nhanh ve {topic}. "
                "Ba y chinh: mot, vi sao no quan trong; "
                "hai, dieu can nho ngay; "
                "ba, mot meo ap dung trong thuc te. "
                "Neu thay huu ich, theo doi de xem them."
            )

        return (
            f"Today we are talking about {topic}. "
            "Three quick takeaways: first, why it matters; "
            "second, the key idea to remember; "
            "third, one practical tip. "
            "If this helps, follow for more."
        )

    @staticmethod
    def _call_openai(
        api_key: str,
        system_prompt: str,
        user_text: str,
        *,
        model: str = "gpt-4o-mini",
    ) -> str:
        logger.info("Calling OpenAI API (%s)...", model)
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _call_groq(
        api_key: str,
        system_prompt: str,
        user_text: str,
        *,
        model: str = "llama-3.3-70b-versatile",
    ) -> str:
        logger.info("Calling Groq API (%s)...", model)
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _call_gemini(
        api_key: str,
        system_prompt: str,
        user_text: str,
        *,
        model: str = "gemini-2.0-flash",
    ) -> str:
        logger.info("Calling Gemini API (%s)...", model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_text}"}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    @staticmethod
    def _call_anthropic(
        api_key: str,
        system_prompt: str,
        user_text: str,
        *,
        model: str = "claude-sonnet-4-20250514",
    ) -> str:
        logger.info("Calling Anthropic API (%s)...", model)
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_text}],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()
