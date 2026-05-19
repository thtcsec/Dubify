"""Gemini ASR provider — cloud speech recognition with speaker diarization using Google Gemini."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiASRService:
    """Transcribe audio using Gemini's multimodal capabilities (audio → text with timestamps)."""

    MODEL = "gemini-2.0-flash"

    SYSTEM_PROMPT = (
        "You are a precise audio transcription engine. "
        "Transcribe the audio into timed segments. "
        "Output ONLY valid JSON — an array of objects with keys: start (float seconds), end (float seconds), text (string), speaker (string like SPEAKER_00). "
        "If you cannot determine speakers, use SPEAKER_00 for all. "
        "Be accurate with timestamps. Do not add commentary."
    )

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY

    def is_available(self) -> bool:
        return bool(self.api_key)

    def transcribe(self, audio_path: Path) -> List[Dict[str, Any]]:
        """Transcribe audio file using Gemini multimodal API."""
        if not self.is_available():
            logger.warning("Gemini ASR: no API key configured.")
            return []

        if not audio_path.exists():
            logger.error("Gemini ASR: audio file not found: %s", audio_path)
            return []

        try:
            return self._call_gemini(audio_path)
        except Exception as e:
            logger.error("Gemini ASR failed: %s", e)
            return []

    def _call_gemini(self, audio_path: Path) -> List[Dict[str, Any]]:
        """Upload audio and get transcription from Gemini."""
        import base64

        # Read and encode audio
        audio_bytes = audio_path.read_bytes()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Determine MIME type
        suffix = audio_path.suffix.lower()
        mime_map = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}
        mime_type = mime_map.get(suffix, "audio/wav")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
                        {"text": self.SYSTEM_PROMPT},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 65536,
            },
        }

        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=300)
        response.raise_for_status()

        result = response.json()
        text_output = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        return self._parse_response(text_output)

    def _parse_response(self, raw: str) -> List[Dict[str, Any]]:
        """Parse Gemini's JSON response into segment list."""
        text = (raw or "").strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            segments = json.loads(text)
            if isinstance(segments, list):
                return [
                    {
                        "start": float(seg.get("start", 0)),
                        "end": float(seg.get("end", 0)),
                        "text": str(seg.get("text", "")).strip(),
                        "speaker": str(seg.get("speaker", "SPEAKER_00")),
                    }
                    for seg in segments
                    if seg.get("text", "").strip()
                ]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Gemini ASR: failed to parse JSON response: %s", e)

        return []
