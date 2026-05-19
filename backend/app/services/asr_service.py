import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings

# Attempt to import faster-whisper. Fallback to standard whisper if needed.
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    import whisper

logger = logging.getLogger(__name__)

class ASRService:
    def __init__(self, model_size: str = "base", device: Optional[str] = None):
        from app.core.gpu import resolve_whisper_device

        self.model_size = model_size
        self.device = device or resolve_whisper_device()
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return
        
        logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
        if HAS_FASTER_WHISPER:
            # compute_type can be float16, int8_float16, int8
            compute_type = "float16" if self.device == "cuda" else "int8"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute_type)
        else:
            self.model = whisper.load_model(self.model_size, device=self.device)

    def transcribe(self, audio_path: Path) -> List[Dict[str, Any]]:
        """Transcribe audio to text segments. Uses WhisperX API if configured, else local Faster-Whisper."""
        
        if settings.WHISPERX_API_URL:
            logger.info(f"Using external WhisperX API for transcription and diarization: {audio_path}")
            try:
                import requests
                # Mock OpenAI-like API call as implemented in pyvideotrans
                url = f"{settings.WHISPERX_API_URL.rstrip('/')}/audio/transcriptions"
                with open(audio_path, "rb") as f:
                    files = {"file": (audio_path.name, f, "audio/wav")}
                    data = {
                        "model": self.model_size,
                        "response_format": "diarized_json"
                    }
                    response = requests.post(url, files=files, data=data, timeout=300)
                    response.raise_for_status()
                    result = response.json()
                
                segments_out = []
                for it in result.get("segments", []):
                    segments_out.append({
                        "start": it.get("start", 0.0),
                        "end": it.get("end", 0.0),
                        "text": it.get("text", "").strip(),
                        "speaker": it.get("speaker", "SPEAKER_00")
                    })
                return segments_out
            except Exception as e:
                logger.error(f"WhisperX API failed, falling back to local Faster-Whisper: {e}")

        self._load_model()
        logger.info(f"Transcribing {audio_path} using local Faster-Whisper...")
        
        segments_out = []
        
        if HAS_FASTER_WHISPER:
            segments, info = self.model.transcribe(
                str(audio_path),
                beam_size=5,
                word_timestamps=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            for segment in segments:
                segments_out.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "speaker": "SPEAKER_00"
                })
        else:
            result = self.model.transcribe(str(audio_path))
            for segment in result['segments']:
                segments_out.append({
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": segment['text'].strip(),
                    "speaker": "SPEAKER_00"
                })
        
        logger.info(f"Transcription completed. Found {len(segments_out)} segments.")

        # If local transcription returned nothing, try Gemini ASR as fallback
        if not segments_out and settings.GEMINI_API_KEY:
            logger.info("Local ASR returned no segments. Trying Gemini ASR fallback...")
            from app.services.gemini_asr_service import GeminiASRService
            gemini_asr = GeminiASRService()
            if gemini_asr.is_available():
                segments_out = gemini_asr.transcribe(audio_path)
                if segments_out:
                    logger.info("Gemini ASR fallback succeeded: %d segments.", len(segments_out))

        return segments_out

    @staticmethod
    def merge_segments_by_sentence(
        segments: List[Dict[str, Any]],
        max_duration: float = 6.5,
        pause_threshold: float = 0.55,
        max_chars: int = 78,
    ) -> List[Dict[str, Any]]:
        """
        Merge Whisper fragments into scene-friendly cues (pause + sentence boundaries).
        """
        import re

        sentence_endings = re.compile(r'[.!?…:;]\s*$')
        merged: List[Dict[str, Any]] = []
        current_group = {"text": "", "start": None, "end": None}

        def flush() -> None:
            nonlocal current_group
            if current_group["text"] and current_group["start"] is not None:
                merged.append(
                    {
                        "text": current_group["text"].strip(),
                        "start": current_group["start"],
                        "end": current_group["end"],
                    }
                )
            current_group = {"text": "", "start": None, "end": None}

        for i, seg in enumerate(segments):
            text = seg["text"].strip()
            if not text:
                continue

            if current_group["start"] is None:
                current_group["start"] = seg["start"]

            if current_group["text"]:
                current_group["text"] += " " + text
            else:
                current_group["text"] = text

            current_group["end"] = seg["end"]

            duration = current_group["end"] - current_group["start"]
            has_sentence_end = bool(sentence_endings.search(text))
            char_count = len(current_group["text"])

            has_pause = False
            if i + 1 < len(segments):
                pause_duration = segments[i + 1]["start"] - seg["end"]
                has_pause = pause_duration >= pause_threshold

            if (
                has_sentence_end
                or duration >= max_duration
                or has_pause
                or char_count >= max_chars
            ):
                flush()

        if current_group["text"]:
            flush()

        return merged

    @staticmethod
    def split_oversized_segments(
        segments: List[Dict[str, Any]],
        max_chars: int = 85,
        max_duration: float = 6.0,
    ) -> List[Dict[str, Any]]:
        """Split long cues so TTS/subtitles stay readable and sync more naturally."""
        result: List[Dict[str, Any]] = []

        for seg in segments:
            text = (seg.get("text") or "").strip()
            start = float(seg["start"])
            end = float(seg["end"])
            duration = max(end - start, 0.05)

            if len(text) <= max_chars and duration <= max_duration:
                result.append({"text": text, "start": start, "end": end})
                continue

            words = text.split()
            chunks: list[str] = []
            buf: list[str] = []
            buf_len = 0
            target_chars = max(28, max_chars // 2)

            for word in words:
                extra = len(word) + (1 if buf else 0)
                if buf and buf_len + extra > target_chars:
                    chunks.append(" ".join(buf))
                    buf = [word]
                    buf_len = len(word)
                else:
                    buf.append(word)
                    buf_len += extra
            if buf:
                chunks.append(" ".join(buf))

            if len(chunks) <= 1:
                result.append({"text": text, "start": start, "end": end})
                continue

            total_weight = sum(max(len(c), 1) for c in chunks)
            cursor = start
            for idx, chunk in enumerate(chunks):
                share = max(len(chunk), 1) / total_weight
                chunk_dur = duration * share
                if idx == len(chunks) - 1:
                    chunk_end = end
                else:
                    chunk_end = min(end, cursor + chunk_dur)
                result.append({"text": chunk, "start": cursor, "end": chunk_end})
                cursor = chunk_end

        return result

    @staticmethod
    def save_transcript(segments: List[Dict[str, Any]], output_path: Path):
        """Save segments to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)
