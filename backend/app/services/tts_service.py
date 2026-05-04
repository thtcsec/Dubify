import logging
import asyncio
import tempfile
import threading
import wave
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from piper import PiperVoice
from app.core.config import settings
from app.services.video_service import VideoService
from app.services.f5_tts_service import F5TTSService
from app.services.text_normalizer import normalize_for_tts

logger = logging.getLogger(__name__)

class TTSService:
    _piper_cache: dict[str, PiperVoice] = {}
    _piper_lock = threading.Lock()

    def __init__(self, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", pitch: str = "+0Hz", provider: str = "edge", target_lang: str = "vi"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.provider = provider
        self.target_lang = target_lang
        self.f5_service = F5TTSService()

    def _use_local_tts(self) -> bool:
        return not settings.allow_network_tts()

    @staticmethod
    def _write_basic_vtt(text: str, audio_path: Path, subtitle_path: Path):
        duration = max(VideoService.get_duration(audio_path), 0.1)
        words = [word for word in text.split() if word.strip()]

        def fmt(seconds: float) -> str:
            total_ms = int(max(seconds, 0) * 1000)
            hours = total_ms // 3_600_000
            minutes = (total_ms % 3_600_000) // 60_000
            secs = (total_ms % 60_000) // 1000
            millis = total_ms % 1000
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

        if not words:
            subtitle_path.write_text("WEBVTT\n\n", encoding="utf-8")
            return

        chunk_size = 6
        chunks = [" ".join(words[index:index + chunk_size]) for index in range(0, len(words), chunk_size)]
        step = duration / len(chunks)
        lines = ["WEBVTT", ""]
        for index, chunk in enumerate(chunks, start=1):
            start = (index - 1) * step
            end = duration if index == len(chunks) else index * step
            lines.append(f"{index}")
            lines.append(f"{fmt(start)} --> {fmt(end)}")
            lines.append(chunk)
            lines.append("")

        subtitle_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _sapi_voice_hint(edge_voice_id: str) -> Optional[str]:
        lowered = (edge_voice_id or "").lower()
        if "female" in lowered or "hoaimy" in lowered or "aria" in lowered or "jenny" in lowered:
            return "female"
        if "male" in lowered or "namminh" in lowered or "guy" in lowered or "liam" in lowered:
            return "male"
        return None

    @staticmethod
    def _voice_locale(edge_voice_id: str) -> Optional[str]:
        parts = (edge_voice_id or "").split("-")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0].lower()}_{parts[1].upper()}"
        return None

    @staticmethod
    def _piper_config_path(model_path: Path) -> Path:
        return Path(f"{model_path}.json")

    def _resolve_piper_model(self) -> Optional[Path]:
        if not settings.PIPER_MODELS_DIR.exists():
            return None

        available_models = [
            model_path
            for model_path in settings.PIPER_MODELS_DIR.rglob("*.onnx")
            if self._piper_config_path(model_path).exists()
        ]
        if not available_models:
            return None

        locale = self._voice_locale(self.voice)
        if locale:
            exact_matches = [
                model_path for model_path in available_models
                if locale in model_path.as_posix() or model_path.name.startswith(f"{locale}-") or model_path.name.startswith(f"{locale}_")
            ]
            if exact_matches:
                return sorted(exact_matches)[0]

            language_prefix = locale.split("_", 1)[0]
            language_matches = [
                model_path for model_path in available_models
                if f"/{language_prefix}/" in model_path.as_posix() or model_path.name.startswith(f"{language_prefix}_")
            ]
            if language_matches:
                return sorted(language_matches)[0]

            return None

        return sorted(available_models)[0] if len(available_models) == 1 else None

    @classmethod
    def _load_piper_voice(cls, model_path: Path) -> PiperVoice:
        model_key = str(model_path.resolve())
        with cls._piper_lock:
            voice = cls._piper_cache.get(model_key)
            if voice is None:
                voice = PiperVoice.load(model_path, config_path=cls._piper_config_path(model_path))
                cls._piper_cache[model_key] = voice
        return voice

    def _generate_piper_audio_sync(self, text: str, output_path: Path) -> bool:
        model_path = self._resolve_piper_model()
        if model_path is None:
            raise RuntimeError("No Piper model is installed for offline TTS.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav_file:
            normalized_text = self._normalize_local_tts_text(text)
            self._load_piper_voice(model_path).synthesize_wav(normalized_text, wav_file)
        return output_path.exists() and output_path.stat().st_size > 0

    def _normalize_local_tts_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.replace("\r", " ").replace("\n", ". ")
        normalized = re.sub(r"https?://\S+", " ", normalized)
        normalized = re.sub(r"\bwww\.\S+\b", " ", normalized)
        normalized = normalized.replace("&", " và ")
        normalized = normalized.replace("%", " phần trăm ")
        normalized = normalized.replace("@", " a còng ")

        locale = self._voice_locale(self.voice) or ""
        if locale.startswith("vi_"):
            digit_map = {
                "0": " không ",
                "1": " một ",
                "2": " hai ",
                "3": " ba ",
                "4": " bốn ",
                "5": " năm ",
                "6": " sáu ",
                "7": " bảy ",
                "8": " tám ",
                "9": " chín ",
            }
        else:
            digit_map = {
                "0": " zero ",
                "1": " one ",
                "2": " two ",
                "3": " three ",
                "4": " four ",
                "5": " five ",
                "6": " six ",
                "7": " seven ",
                "8": " eight ",
                "9": " nine ",
            }

        normalized = "".join(digit_map.get(char, char) for char in normalized)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        normalized = re.sub(r"[^\w\s,.!?;:()/%-]", " ", normalized, flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized or "..."

    def _generate_local_audio_sync(self, text: str, output_path: Path) -> bool:
        import pythoncom
        import pyttsx3

        temp_output = output_path if output_path.suffix.lower() == ".wav" else output_path.with_suffix(".wav")

        try:
            if self._generate_piper_audio_sync(text, temp_output):
                if temp_output != output_path:
                    temp_output.replace(output_path)
                return output_path.exists() and output_path.stat().st_size > 0
        except Exception as exc:
            logger.warning("Piper local TTS failed, falling back to system voices: %s", exc)

        pythoncom.CoInitialize()

        try:
            try:
                engine = pyttsx3.init()
                try:
                    rate_value = int(engine.getProperty("rate"))
                    engine.setProperty("rate", max(120, min(220, rate_value)))
                except Exception:
                    logger.debug("Could not adjust local TTS rate.")

                voice_hint = self._sapi_voice_hint(self.voice)
                if voice_hint:
                    try:
                        for voice in engine.getProperty("voices"):
                            name = (getattr(voice, "name", "") or "").lower()
                            voice_id = (getattr(voice, "id", "") or "").lower()
                            if voice_hint in name or voice_hint in voice_id:
                                engine.setProperty("voice", voice.id)
                                break
                    except Exception:
                        logger.debug("Could not match local SAPI voice for hint '%s'.", voice_hint)

                engine.save_to_file(text, str(temp_output))
                engine.runAndWait()
                if temp_output.exists() and temp_output.stat().st_size > 0:
                    if temp_output != output_path:
                        temp_output.replace(output_path)
                    return output_path.exists() and output_path.stat().st_size > 0
            except Exception as exc:
                logger.warning("pyttsx3 local TTS failed, falling back to PowerShell SAPI: %s", exc)

            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as text_file:
                text_file.write(text)
                text_path = Path(text_file.name)

            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "$text = Get-Content -Raw -Encoding UTF8 '{text_path}'; "
                "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$synth.SetOutputToWaveFile('{output_path}'); "
                "$synth.Speak($text); "
                "$synth.Dispose()"
            ).format(
                text_path=str(text_path).replace("'", "''"),
                output_path=str(temp_output).replace("'", "''"),
            )

            try:
                import subprocess
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "PowerShell SAPI returned a non-zero exit code.")
                if temp_output.exists() and temp_output.stat().st_size > 0:
                    if temp_output != output_path:
                        temp_output.replace(output_path)
                    return output_path.exists() and output_path.stat().st_size > 0
                raise RuntimeError("PowerShell SAPI did not produce any audio file.")
            finally:
                text_path.unlink(missing_ok=True)
        finally:
            pythoncom.CoUninitialize()

    async def _generate_local_audio(self, text: str, output_path: Path) -> bool:
        return await asyncio.to_thread(self._generate_local_audio_sync, text, output_path)

    async def generate_audio(self, text: str, output_path: Path, ref_audio_path: Optional[Path] = None, ref_text: Optional[str] = None, retries: int = 3) -> bool:
        """Generate audio for a single text string using Edge-TTS or F5-TTS with retries."""
        if not text.strip():
            logger.warning("Empty text passed to TTS, skipping.")
            return False
        
        # Normalize text for TTS (numbers→words, dates, acronyms, loanwords)
        text = normalize_for_tts(text, self.target_lang)
            
        if self.provider == "f5tts" and self.f5_service.is_available() and ref_audio_path and ref_text:
            return await self.f5_service.clone_voice(ref_audio_path, ref_text, text, output_path)

        if self._use_local_tts():
            try:
                return await self._generate_local_audio(text, output_path)
            except Exception as e:
                logger.error(f"Local TTS failed: {e}")
                return False

        # Use subprocess to avoid uvicorn event loop conflicts on Windows
        for attempt in range(retries):
            try:
                success = await self._edge_tts_subprocess(text, self.voice, output_path)
                if success:
                    return True
                logger.warning(f"TTS attempt {attempt + 1} produced empty file for: {text[:50]}...")
            except Exception as e:
                logger.error(f"Edge-TTS attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
        
        return False

    async def generate_audio_with_subtitles(self, text: str, target_lang: str, job_id: str) -> Tuple[Path, Path]:
        """Generate audio and subtitles using the active TTS backend."""
        # Normalize text for TTS before generating audio
        text = normalize_for_tts(text, target_lang)
        if self._use_local_tts():
            audio_path = settings.TEMP_DIR / f"{job_id}_tts.wav"
            srt_path = settings.TEMP_DIR / f"{job_id}_tts.vtt"
            success = await self._generate_local_audio(text, audio_path)
            if not success:
                raise RuntimeError("Local TTS could not generate audio.")
            self._write_basic_vtt(text, audio_path, srt_path)
            return audio_path, srt_path

        audio_path = settings.TEMP_DIR / f"{job_id}_tts.mp3"
        srt_path = settings.TEMP_DIR / f"{job_id}_tts.vtt"

        try:
            # Use subprocess for edge-tts to avoid event loop conflicts
            success = await self._edge_tts_subprocess(text, self.voice, audio_path, srt_path)
            if not success:
                raise RuntimeError("Edge-TTS subprocess produced no audio.")
            return audio_path, srt_path
        except Exception as e:
            logger.warning("Edge-TTS subtitle generation failed, falling back to local TTS: %s", e)
            fallback_audio = settings.TEMP_DIR / f"{job_id}_tts.wav"
            fallback_srt = settings.TEMP_DIR / f"{job_id}_tts.vtt"
            success = await self._generate_local_audio(text, fallback_audio)
            if not success:
                logger.error("Edge-TTS Subtitle Gen error: %s", e)
                raise RuntimeError(f"Could not generate audio via Edge-TTS or local fallback: {e}") from e
            self._write_basic_vtt(text, fallback_audio, fallback_srt)
            return fallback_audio, fallback_srt

    @staticmethod
    async def _edge_tts_subprocess(
        text: str,
        voice: str,
        audio_path: Path,
        subtitle_path: Optional[Path] = None,
    ) -> bool:
        """Run edge-tts via CLI subprocess to avoid uvicorn event loop conflicts on Windows."""
        import sys
        import tempfile

        # Write text to a temp file to handle Unicode and long texts safely
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(text)
            text_file = Path(tf.name)

        try:
            args = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice,
                "--file", str(text_file),
                "--write-media", str(audio_path),
            ]
            if subtitle_path:
                args.extend(["--write-subtitles", str(subtitle_path)])

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.error("Edge-TTS CLI timed out after 60s")
                raise RuntimeError("Edge-TTS timed out")

            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip()
                logger.error(f"Edge-TTS CLI failed: {err}")
                raise RuntimeError(f"Edge-TTS CLI error: {err}")

            if not audio_path.exists() or audio_path.stat().st_size == 0:
                return False

            return True
        finally:
            text_file.unlink(missing_ok=True)

    async def process_segments(
        self,
        segments: List[Dict[str, Any]],
        temp_dir: Path,
        max_concurrency: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Path]:
        """
        Generate audio for all segments in parallel and align them with original timing.
        Returns list of paths to final aligned audio segments (1:1 mapping with input).
        """
        if self._use_local_tts():
            max_concurrency = 1

        logger.info(f"Generating TTS for {len(segments)} segments (concurrency={max_concurrency})")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        completed_count = 0
        completed_lock = asyncio.Lock()

        async def process_single_segment(i: int, seg: Dict[str, Any]) -> Path:
            async with semaphore:
                text = seg.get('translated_text', seg['text'])
                target_duration = seg['end'] - seg['start']
                
                raw_suffix = ".wav" if self._use_local_tts() else ".mp3"
                raw_path = temp_dir / f"tts_{i}_raw{raw_suffix}"
                aligned_path = temp_dir / f"tts_{i}_aligned.wav"
                
                # 1. Generate Raw TTS
                # Extract ref_audio and ref_text for voice cloning if they exist in the segment dict
                ref_audio = Path(seg['ref_audio']) if 'ref_audio' in seg and seg['ref_audio'] else None
                ref_text = seg.get('text', '')
                
                success = await self.generate_audio(text, raw_path, ref_audio_path=ref_audio, ref_text=ref_text)
                
                if success:
                    # 2. Time-stretch to match original duration
                    try:
                        VideoService.stretch_audio(raw_path, aligned_path, target_duration)
                        if aligned_path.exists():
                            return aligned_path
                    except Exception as e:
                        logger.error(f"Error stretching audio for segment {i}: {e}")
                
                # Fallback: Create silence if TTS or stretching fails
                logger.warning(f"Using silence fallback for segment {i}")
                VideoService.create_silence(target_duration, aligned_path)
                return aligned_path

        async def wrap_segment(i: int, seg: Dict[str, Any]) -> Path:
            nonlocal completed_count
            path = await process_single_segment(i, seg)
            async with completed_lock:
                if path.exists():
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, len(segments))
            return path

        tasks = [wrap_segment(i, seg) for i, seg in enumerate(segments)]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"TTS generation complete. Processed {len(results)} segments.")
        return results

    @staticmethod
    def create_concat_list(audio_paths: List[Path], segments: List[Dict[str, Any]], output_list_file: Path, temp_dir: Path):
        """
        Create a concat file for FFmpeg, including silent gaps to maintain sync.
        Logic: if (current_start - previous_end) > threshold, add silence.
        """
        with open(output_list_file, 'w', encoding='utf-8') as f:
            last_end = 0.0
            for i, (path, seg) in enumerate(zip(audio_paths, segments)):
                start = seg['start']
                gap = start - last_end
                
                # If gap is significant (> 10ms), insert a silent file
                if gap > 0.01:
                    silence_path = temp_dir / f"gap_{i}.wav"
                    VideoService.create_silence(gap, silence_path)
                    f.write(f"file '{silence_path.absolute()}'\n")
                
                f.write(f"file '{path.absolute()}'\n")
                last_end = seg['end']
                
        logger.info(f"Concat list created at {output_list_file} with sync gaps.")
