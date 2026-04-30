import logging
import requests
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Multi-provider LLM service. Auto-selects: Groq > OpenAI > Gemini > raw fallback."""

    @staticmethod
    def _get_provider() -> tuple:
        """Return (provider_name, api_key) for the first available provider."""
        if settings.GROQ_API_KEY:
            return "groq", settings.GROQ_API_KEY
        if settings.OPENAI_API_KEY:
            return "openai", settings.OPENAI_API_KEY
        if settings.GEMINI_API_KEY:
            return "gemini", settings.GEMINI_API_KEY
        return "none", ""

    @staticmethod
    def generate_news_script(raw_text: str, target_lang: str = "vi") -> str:
        """
        Rewrite raw news text into an engaging, professional news script.
        Falls back to raw text if no API key is configured.
        """
        if not settings.allow_cloud_llm():
            logger.info("Processing mode does not allow cloud LLM rewrite. Returning raw text.")
            return raw_text.strip()

        provider, api_key = LLMService._get_provider()

        if provider == "none":
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
        except Exception as e:
            logger.error(f"LLM ({provider}) failed: {e}")
            return raw_text.strip()
        return raw_text.strip()

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
    def _call_openai(api_key: str, system_prompt: str, user_text: str) -> str:
        logger.info("Calling OpenAI API...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
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
    def _call_groq(api_key: str, system_prompt: str, user_text: str) -> str:
        logger.info("Calling Groq API (ultra-fast)...")
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
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
    def _call_gemini(api_key: str, system_prompt: str, user_text: str) -> str:
        logger.info("Calling Gemini API...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
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
