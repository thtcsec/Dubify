import logging
import asyncio
from pathlib import Path
from typing import Optional

try:
    from gradio_client import Client, handle_file
except ImportError:
    Client = None
    handle_file = None

from app.core.config import settings

logger = logging.getLogger(__name__)

class F5TTSService:
    """Service to connect to a local or remote F5-TTS instance via Gradio API."""
    def __init__(self):
        self.api_url = settings.F5TTS_API_URL
        self.client = None
        if self.api_url and Client is not None:
            try:
                self.client = Client(self.api_url, httpx_kwargs={"timeout": 300}, ssl_verify=False)
            except Exception as e:
                logger.error(f"Failed to initialize F5-TTS client: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    async def clone_voice(self, ref_audio_path: Path, ref_text: str, target_text: str, output_path: Path) -> bool:
        """
        Uses Zero-shot voice cloning to generate audio that sounds like the reference audio.
        """
        if not self.is_available():
            logger.error("F5-TTS is not configured or gradio_client is missing.")
            return False

        try:
            logger.info(f"Sending voice clone request to F5-TTS for text: {target_text[:30]}...")
            # Use asyncio.to_thread since gradio_client is synchronous
            result = await asyncio.to_thread(
                self.client.predict,
                ref_audio_input=handle_file(str(ref_audio_path)),
                ref_text_input=ref_text,
                gen_text_input=target_text,
                remove_silence=True,
                randomize_seed=True,
                seed_input=0,
                cross_fade_duration_slider=0.1,
                nfe_slider=32,
                speed_slider=1.0,
                api_name='/basic_tts'
            )
            
            # The result is usually a tuple containing the path to the generated audio
            wav_file = result[0] if isinstance(result, (list, tuple)) and result else result
            if isinstance(wav_file, dict) and "value" in wav_file:
                wav_file = wav_file['value']
                
            if isinstance(wav_file, str) and Path(wav_file).is_file():
                # Copy the generated file to our desired output path
                import shutil
                shutil.copy2(wav_file, output_path)
                return True
            else:
                logger.error(f"F5-TTS returned unexpected result format: {result}")
                return False
                
        except Exception as e:
            logger.error(f"F5-TTS cloning failed: {e}")
            return False
