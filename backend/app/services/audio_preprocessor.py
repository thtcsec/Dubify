"""Audio Preprocessor — clean audio before ASR using sherpa-onnx UVR source separation.

Separates vocals from background music/noise for cleaner transcription.
Pattern adapted from pyvideotrans/process/prepare_audio.py.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """Separate vocals from background using sherpa-onnx UVR model (CPU-only)."""

    DEFAULT_MODEL = "UVR-MDX-NET-Inst_HQ_4"

    def __init__(self, model_name: str = ""):
        self.model_name = model_name or self.DEFAULT_MODEL

    def is_available(self) -> bool:
        """Check if sherpa-onnx and the UVR model are available."""
        try:
            import sherpa_onnx  # noqa: F401
        except ImportError:
            return False

        model_path = self._model_path()
        return model_path.exists()

    def separate_vocals(
        self,
        input_audio: Path,
        output_dir: Path,
    ) -> Tuple[Optional[Path], Optional[Path]]:
        """Separate audio into vocals and instrumental tracks.

        Returns (vocals_path, instrumental_path) or (None, None) on failure.
        """
        if not self.is_available():
            logger.warning(
                "Audio preprocessor unavailable. Install sherpa-onnx and download UVR model to: %s",
                self._model_path(),
            )
            return None, None

        try:
            import numpy as np
            import sherpa_onnx
            import soundfile as sf

            model_path = self._model_path()
            output_dir.mkdir(parents=True, exist_ok=True)

            vocals_path = output_dir / "vocals_clean.wav"
            instrumental_path = output_dir / "instrumental.wav"

            logger.info("Audio preprocessing: separating vocals from %s", input_audio.name)
            start_time = time.time()

            # Create separator
            config = sherpa_onnx.OfflineSourceSeparationConfig(
                model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                    uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(
                        model=str(model_path),
                    ),
                    num_threads=4,
                    debug=False,
                    provider="cpu",
                ),
            )
            if not config.validate():
                logger.error("Invalid sherpa-onnx UVR config.")
                return None, None

            separator = sherpa_onnx.OfflineSourceSeparation(config)

            # Load audio
            samples, sample_rate = sf.read(str(input_audio), dtype="float32", always_2d=True)
            samples = np.transpose(samples)
            samples = np.ascontiguousarray(samples)

            # Process
            output = separator.process(sample_rate=sample_rate, samples=samples)

            # stems[0] = instrumental, stems[1] = vocals
            instrumental = np.transpose(output.stems[0].data)
            vocals = np.transpose(output.stems[1].data)

            sf.write(str(vocals_path), vocals, samplerate=output.sample_rate)
            sf.write(str(instrumental_path), instrumental, samplerate=output.sample_rate)

            elapsed = time.time() - start_time
            logger.info(
                "Audio preprocessing complete: %.1fs. Vocals: %s, Instrumental: %s",
                elapsed,
                vocals_path.name,
                instrumental_path.name,
            )

            # Cleanup
            del separator
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            import gc
            gc.collect()

            return vocals_path, instrumental_path

        except Exception as e:
            logger.error("Audio preprocessing failed: %s", e, exc_info=True)
            return None, None

    def _model_path(self) -> Path:
        """Expected model file path."""
        models_dir = settings.MODELS_DIR / "onnx"
        return models_dir / f"{self.model_name}.onnx"
