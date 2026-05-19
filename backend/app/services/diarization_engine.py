"""Speaker Diarization Engine — identify and label distinct speakers in audio.

Requirement 17 (Simplified): Label speakers only — no automatic voice assignment.
Uses sherpa-onnx built-in speaker diarization (CPU-only) as default backend.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """A time-stamped segment with speaker label."""
    start_ms: int
    end_ms: int
    speaker: str  # e.g. "SPEAKER_0", "SPEAKER_1"

    @property
    def start_seconds(self) -> float:
        return self.start_ms / 1000.0

    @property
    def end_seconds(self) -> float:
        return self.end_ms / 1000.0


class DiarizationEngine:
    """Identify speakers in audio — label-only (no auto voice assignment).

    Backends:
    1. sherpa-onnx built-in (CPU, no HuggingFace token needed)
    2. WhisperX API (if WHISPERX_API_URL configured)
    """

    def __init__(self, num_speakers: int = -1, language: str = "auto"):
        self.num_speakers = num_speakers  # -1 = auto-detect
        self.language = language

    def is_available(self) -> bool:
        """Check if any diarization backend is available."""
        if settings.WHISPERX_API_URL:
            return True
        try:
            import sherpa_onnx  # noqa: F401
            return self._segmentation_model_exists()
        except ImportError:
            return False

    def diarize(self, audio_path: Path) -> List[SpeakerSegment]:
        """Run speaker diarization on audio file.

        Returns list of SpeakerSegment with time ranges and speaker labels.
        Returns empty list on failure (pipeline continues normally).
        """
        if not audio_path.exists():
            logger.error("Diarization: audio file not found: %s", audio_path)
            return []

        # Try WhisperX API first (if configured)
        if settings.WHISPERX_API_URL:
            result = self._diarize_whisperx(audio_path)
            if result:
                return result

        # Try sherpa-onnx built-in
        result = self._diarize_sherpa(audio_path)
        return result

    def assign_speakers_to_segments(
        self,
        segments: List[Dict],
        diarization: List[SpeakerSegment],
    ) -> List[Dict]:
        """Tag ASR segments with speaker labels based on overlap.

        Each segment gets the speaker with maximum time overlap.
        """
        if not diarization:
            return segments

        for seg in segments:
            seg_start = int(seg.get("start", 0) * 1000)
            seg_end = int(seg.get("end", 0) * 1000)
            seg_duration = seg_end - seg_start

            if seg_duration <= 0:
                seg["speaker"] = "SPEAKER_0"
                continue

            # Find speaker with maximum overlap
            overlaps: Dict[str, int] = {}
            for dia in diarization:
                overlap_start = max(seg_start, dia.start_ms)
                overlap_end = min(seg_end, dia.end_ms)
                overlap = max(0, overlap_end - overlap_start)
                if overlap > 0:
                    overlaps[dia.speaker] = overlaps.get(dia.speaker, 0) + overlap

            if overlaps:
                seg["speaker"] = max(overlaps, key=overlaps.get)
            else:
                seg["speaker"] = "SPEAKER_0"

        num_speakers = len(set(seg.get("speaker", "SPEAKER_0") for seg in segments))
        logger.info("Diarization: assigned %d speakers to %d segments.", num_speakers, len(segments))
        return segments

    def _diarize_whisperx(self, audio_path: Path) -> List[SpeakerSegment]:
        """Diarize using external WhisperX API."""
        try:
            import requests
            url = f"{settings.WHISPERX_API_URL.rstrip('/')}/audio/transcriptions"
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                data = {"model": "base", "response_format": "diarized_json"}
                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()
                result = response.json()

            segments = []
            for item in result.get("segments", []):
                segments.append(SpeakerSegment(
                    start_ms=int(item.get("start", 0) * 1000),
                    end_ms=int(item.get("end", 0) * 1000),
                    speaker=item.get("speaker", "SPEAKER_0"),
                ))
            logger.info("WhisperX diarization: %d segments.", len(segments))
            return segments
        except Exception as e:
            logger.warning("WhisperX diarization failed: %s", e)
            return []

    def _diarize_sherpa(self, audio_path: Path) -> List[SpeakerSegment]:
        """Diarize using sherpa-onnx built-in model (CPU-only)."""
        try:
            import sherpa_onnx
            import soundfile as sf
            import numpy as np

            if not self._segmentation_model_exists():
                logger.warning("Sherpa-onnx segmentation model not found.")
                return []

            start_time = time.time()
            logger.info("Running sherpa-onnx speaker diarization...")

            seg_model = str(settings.MODELS_DIR / "onnx" / "seg_model.onnx")
            # Use English embedding model as default
            embed_model = str(settings.MODELS_DIR / "onnx" / "nemo_en_titanet_small.onnx")
            if not Path(embed_model).exists():
                # Try Chinese model
                embed_model = str(settings.MODELS_DIR / "onnx" / "3dspeaker_speech_eres2net_large_sv_zh-cn_3dspeaker_16k.onnx")
                if not Path(embed_model).exists():
                    logger.warning("No speaker embedding model found.")
                    return []

            config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                    pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                        model=seg_model,
                    ),
                ),
                embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=embed_model),
                clustering=sherpa_onnx.FastClusteringConfig(
                    num_clusters=self.num_speakers if self.num_speakers > 0 else -1,
                    threshold=0.5,
                ),
                min_duration_on=0.3,
                min_duration_off=0.5,
            )

            if not config.validate():
                logger.error("Invalid sherpa-onnx diarization config.")
                return []

            sd = sherpa_onnx.OfflineSpeakerDiarization(config)

            # Load audio
            audio, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
            audio = audio[:, 0]  # mono

            # Resample if needed
            if sample_rate != sd.sample_rate:
                try:
                    import librosa
                    audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=sd.sample_rate)
                except ImportError:
                    logger.warning("librosa not available for resampling.")
                    return []

            result = sd.process(audio).sort_by_start_time()

            segments = []
            for r in result:
                segments.append(SpeakerSegment(
                    start_ms=int(r.start * 1000),
                    end_ms=int(r.end * 1000),
                    speaker=f"SPEAKER_{r.speaker}",
                ))

            elapsed = time.time() - start_time
            num_speakers = len(set(s.speaker for s in segments))
            logger.info(
                "Sherpa diarization: %d segments, %d speakers, %.1fs.",
                len(segments), num_speakers, elapsed,
            )
            return segments

        except Exception as e:
            logger.error("Sherpa-onnx diarization failed: %s", e, exc_info=True)
            return []

    @staticmethod
    def _segmentation_model_exists() -> bool:
        """Check if the segmentation model file exists."""
        return (settings.MODELS_DIR / "onnx" / "seg_model.onnx").exists()
