"""Catalog of LLM models for Settings + Studio rewrite."""

from __future__ import annotations

from typing import Any

# id format: "provider:model_id"
LLM_MODEL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "groq:llama-3.3-70b-versatile",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B (Groq)",
        "tier": "strong",
        "best_for": "Studio script rewrite, tiếng Việt nhanh, hook viral",
        "speed": "fast",
    },
    {
        "id": "groq:llama-3.1-8b-instant",
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B Instant (Groq)",
        "tier": "light",
        "best_for": "Nháp nhanh, script ngắn, ít quota",
        "speed": "fastest",
    },
    {
        "id": "openai:gpt-4o-mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "name": "GPT-4o mini",
        "tier": "strong",
        "best_for": "Kịch bản sắc, cấu trúc scene, tiếng Anh/Việt",
        "speed": "medium",
    },
    {
        "id": "openai:gpt-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "name": "GPT-4o",
        "tier": "premium",
        "best_for": "Nội dung phức tạp, số liệu, tone chuyên nghiệp",
        "speed": "medium",
    },
    {
        "id": "gemini:gemini-2.0-flash",
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "tier": "strong",
        "best_for": "Tin tức, tóm tắt dài, đa ngôn ngữ",
        "speed": "fast",
    },
    {
        "id": "gemini:gemini-1.5-flash",
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "tier": "light",
        "best_for": "Rewrite nhẹ, tiết kiệm quota",
        "speed": "fast",
    },
    {
        "id": "anthropic:claude-sonnet-4-20250514",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "tier": "premium",
        "best_for": "Kịch bản dài, logic, giọng anchor tự nhiên",
        "speed": "medium",
    },
    {
        "id": "ollama:llama3",
        "provider": "ollama",
        "model": "llama3",
        "name": "Ollama (local)",
        "tier": "local",
        "best_for": "Offline, không API key — cần Ollama chạy local",
        "speed": "depends",
    },
]


def parse_llm_model_id(model_id: str) -> tuple[str, str]:
    if ":" in model_id:
        provider, model = model_id.split(":", 1)
        return provider.strip().lower(), model.strip()
    return "auto", model_id.strip()


def catalog_entry(model_id: str) -> dict[str, Any] | None:
    for entry in LLM_MODEL_CATALOG:
        if entry["id"] == model_id:
            return entry
    return None
