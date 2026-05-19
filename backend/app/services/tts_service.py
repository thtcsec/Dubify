import logging
import asyncio
import shutil
import subprocess
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
from app.utils.script_split import split_spoken_lines

logger = logging.getLogger(__name__)


def _studio_vtt_ts(seconds: float) -> str:
    total_ms = int(max(seconds, 0) * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# Default Edge-TTS voices per target language (dubbing uses these when no voice_id is sent).
# Alternate voices tried when the primary Edge voice returns NoAudioReceived.
ALT_EDGE_VOICES: dict[str, list[str]] = {
    "vi": ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"],
    "en": ["en-US-JennyNeural", "en-US-GuyNeural"],
}

DEFAULT_EDGE_VOICES: dict[str, str] = {
    "vi": "vi-VN-NamMinhNeural",
    "en": "en-US-JennyNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "de": "de-DE-KatjaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "it": "it-IT-ElsaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "th": "th-TH-PremwadeeNeural",
    "hi": "hi-IN-SwaraNeural",
    "ar": "ar-SA-ZariyahNeural",
    "id": "id-ID-GadisNeural",
}


class TTSService:
    _piper_cache: dict[str, PiperVoice] = {}
    _piper_lock = threading.Lock()

    @staticmethod
    def default_voice_for_lang(target_lang: str) -> str:
        code = (target_lang or "vi").split("-")[0].lower()
        return DEFAULT_EDGE_VOICES.get(code, "en-US-JennyNeural")

    def __init__(
        self,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        provider: str = "edge",
        target_lang: str = "vi",
    ):
        self.voice = voice or self.default_voice_for_lang(target_lang)
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
        chunks = split_spoken_lines(text, max_chars=90)
        if not chunks:
            chunks = [segment for segment in text.split() if segment.strip()]

        def fmt(seconds: float) -> str:
            total_ms = int(max(seconds, 0) * 1000)
            hours = total_ms // 3_600_000
            minutes = (total_ms % 3_600_000) // 60_000
            secs = (total_ms % 60_000) // 1000
            millis = total_ms % 1000
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

        if not chunks:
            subtitle_path.write_text("WEBVTT\n\n", encoding="utf-8")
            return
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

    @staticmethod
    def _target_lang_to_piper_locale(target_lang: str) -> Optional[str]:
        mapping = {
            "vi": "vi_VN",
            "en": "en_US",
            "ja": "ja_JP",
            "ko": "ko_KR",
            "zh": "zh_CN",
            "fr": "fr_FR",
            "es": "es_ES",
            "de": "de_DE",
            "pt": "pt_BR",
            "it": "it_IT",
            "ru": "ru_RU",
            "th": "th_TH",
            "hi": "hi_IN",
            "ar": "ar_SA",
            "id": "id_ID",
        }
        return mapping.get((target_lang or "").split("-")[0].lower())

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

        locale = self._target_lang_to_piper_locale(self.target_lang) or self._voice_locale(self.voice)
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
        
        text = self._sanitize_for_edge_tts(text)
        text = normalize_for_tts(text, self.target_lang)
        text = self._sanitize_for_edge_tts(text)
            
        if self.provider == "f5tts" and self.f5_service.is_available() and ref_audio_path and ref_text:
            if await self.f5_service.clone_voice(ref_audio_path, ref_text, text, output_path):
                return True
            logger.warning(f"F5TTS cloning failed for text '{text[:20]}...', falling back to default TTS provider.")

        # OpenAI TTS provider (highest quality)
        if self.provider == "openai_tts" or (self.provider == "edge" and settings.OPENAI_API_KEY and not self._use_local_tts()):
            from app.services.openai_tts_service import OpenAITTSService
            openai_tts = OpenAITTSService(
                voice=settings.OPENAI_TTS_VOICE,
                model=settings.OPENAI_TTS_MODEL,
            )
            if self.provider == "openai_tts" and openai_tts.is_available():
                success = await openai_tts.generate(text, output_path)
                if success:
                    return True
                logger.warning("OpenAI TTS failed, falling back to Edge-TTS.")

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
                    await asyncio.sleep(2 ** attempt)

        # Network Edge-TTS failed — try offline Piper/SAPI before giving up.
        try:
            if await self._generate_local_audio(text, output_path):
                logger.info("Edge-TTS unavailable; used local TTS fallback.")
                return True
        except Exception as local_err:
            logger.warning("Local TTS fallback failed: %s", local_err)

        return False

    async def generate_studio_audio_with_subtitles(
        self, text: str, target_lang: str, job_id: str
    ) -> Tuple[Path, Path]:
        """Full-length studio TTS: chunk long scripts instead of truncating to 280 chars."""
        from app.utils.script_split import split_spoken_lines

        from app.utils.studio_script_format import strip_popup_markers_for_tts

        text = strip_popup_markers_for_tts(text)
        text = self._sanitize_for_edge_tts(text)
        text = normalize_for_tts(text, target_lang, transliterate=False)
        text = self._sanitize_for_edge_tts(text)
        lines = split_spoken_lines(text, max_chars=100)
        if not lines:
            lines = [text.strip()] if text.strip() else [""]

        chunks: list[str] = []
        buf: list[str] = []
        buf_len = 0
        max_chunk = 100
        for line in lines:
            extra = len(line) + (1 if buf else 0)
            if buf and buf_len + extra > max_chunk:
                chunks.append(" ".join(buf))
                buf = [line]
                buf_len = len(line)
            else:
                buf.append(line)
                buf_len += extra
        if buf:
            chunks.append(" ".join(buf))

        temp_dir = settings.TEMP_DIR / f"{job_id}_studio_tts"
        temp_dir.mkdir(parents=True, exist_ok=True)
        chunk_paths: list[Path] = []
        vtt_lines = ["WEBVTT", ""]
        timeline = 0.0

        for index, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            chunk_audio = temp_dir / f"chunk_{index:03d}.mp3"
            chunk_vtt = temp_dir / f"chunk_{index:03d}.vtt"
            # Studio builds VTT from chunk durations — Edge subtitles per chunk are not needed.
            ok = await self._edge_tts_subprocess(
                chunk, self.voice, chunk_audio, subtitle_path=None, max_chars=None
            )
            if not ok:
                await asyncio.sleep(0.8)
                ok = await self._edge_tts_subprocess(
                    chunk, self.voice, chunk_audio, subtitle_path=None, max_chars=100, retries=3
                )
            if not ok:
                shorter = self._edge_safe_text(chunk, max_chars=80)
                if shorter and shorter != chunk:
                    ok = await self._edge_tts_subprocess(
                        shorter, self.voice, chunk_audio, subtitle_path=None, max_chars=None, retries=2
                    )
            if not ok:
                ok = await self._generate_local_audio(chunk, chunk_audio.with_suffix(".wav"))
                if ok:
                    chunk_audio = chunk_audio.with_suffix(".wav")
                    self._write_basic_vtt(chunk, chunk_audio, chunk_vtt)
            if not ok or not chunk_audio.exists():
                logger.warning("Studio TTS chunk %d failed, skipping", index)
                continue

            if index + 1 < len(chunks):
                await asyncio.sleep(0.35)

            dur = max(VideoService.get_duration(chunk_audio), 0.05)
            chunk_paths.append(chunk_audio)
            vtt_lines.append(str(len(chunk_paths)))
            vtt_lines.append(f"{_studio_vtt_ts(timeline)} --> {_studio_vtt_ts(timeline + dur)}")
            vtt_lines.append(chunk)
            vtt_lines.append("")
            timeline += dur

        if not chunk_paths:
            raise RuntimeError("Studio TTS produced no audio chunks.")

        final_audio = settings.TEMP_DIR / f"{job_id}_tts.mp3"
        if len(chunk_paths) == 1:
            src = chunk_paths[0]
            if src.suffix.lower() == ".wav":
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "2", str(final_audio)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            else:
                shutil.copy2(src, final_audio)
        else:
            list_file = temp_dir / "chunks.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for p in chunk_paths:
                    f.write(f"file '{p.resolve().as_posix()}'\n")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(final_audio),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

        final_vtt = settings.TEMP_DIR / f"{job_id}_tts.vtt"
        final_vtt.write_text("\n".join(vtt_lines), encoding="utf-8")
        logger.info(
            "Studio TTS complete: %d chunks, %.1fs total",
            len(chunk_paths),
            VideoService.get_duration(final_audio),
        )
        return final_audio, final_vtt

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
    def _strip_studio_section_markers(text: str) -> str:
        """Remove [Scene Title] lines from spoken TTS (kept for HTML scene parsing only)."""
        without_headers = re.sub(r"^\s*\[[^\]]+\]\s*$", "", text or "", flags=re.MULTILINE)
        return re.sub(r"\n{3,}", "\n\n", without_headers).strip()

    def _edge_voice_fallbacks(self, primary_voice: str) -> list[str]:
        """Build fallback voice list — prioritize same gender as primary."""
        voices: list[str] = []
        # Primary voice first
        if primary_voice and primary_voice not in voices:
            voices.append(primary_voice)
        # Same-gender default (don't switch male→female)
        default = self.default_voice_for_lang(self.target_lang)
        if default and default not in voices:
            # Only add default if same gender hint or if primary is empty
            if not primary_voice or self._same_gender(primary_voice, default):
                voices.append(default)
        # Alt voices — filter by same gender
        lang = (self.target_lang or "vi").split("-")[0].lower()
        for candidate in ALT_EDGE_VOICES.get(lang, []):
            if candidate not in voices:
                if not primary_voice or self._same_gender(primary_voice, candidate):
                    voices.append(candidate)
        # If still only 1 voice, add all alts as last resort
        if len(voices) < 2:
            for candidate in ALT_EDGE_VOICES.get(lang, []):
                if candidate not in voices:
                    voices.append(candidate)
        return voices

    @staticmethod
    def _same_gender(voice_a: str, voice_b: str) -> bool:
        """Check if two Edge-TTS voice IDs are likely the same gender."""
        # Edge voice naming: xx-XX-NameNeural — male names tend to have specific patterns
        male_hints = {"namminh", "guy", "liam", "keita", "injoon", "yunxi", "henri", "alvaro",
                      "conrad", "antonio", "diego", "dmitry", "niwat", "madhur", "hamed", "ardi"}
        a_lower = voice_a.lower()
        b_lower = voice_b.lower()
        a_is_male = any(h in a_lower for h in male_hints)
        b_is_male = any(h in b_lower for h in male_hints)
        return a_is_male == b_is_male

    @staticmethod
    def _sanitize_for_edge_tts(text: str) -> str:
        """Edge-TTS returns NoAudioReceived for [] or lone '[' — common with [Section] markers."""
        cleaned = unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n")
        cleaned = re.sub(r"[\u200b-\u200d\ufeff]", "", cleaned)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)  # markdown links
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)  # markdown images
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"\[\s*\]", " ", cleaned)
        cleaned = re.sub(r"\[([^\]]{1,200})\]", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\w)\[(?!\w)", " ", cleaned)
        cleaned = re.sub(r"(?<!\w)\](?!\w)", " ", cleaned)
        cleaned = re.sub(r"[#_|`~<>{}]", " ", cleaned)
        cleaned = re.sub(r"[\u2018\u2019\u201a\u201b\u2032`]", " ", cleaned)
        cleaned = re.sub(r'[\u201c\u201d"]', " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned in {"[]", "[", "]"}:
            return ""
        try:
            from edge_tts.communicate import remove_incompatible_characters

            cleaned = remove_incompatible_characters(cleaned)
        except Exception:
            pass
        return cleaned.strip()

    def _edge_tts_sync_api(
        self,
        text: str,
        voice: str,
        audio_path: Path,
        subtitle_path: Optional[Path] = None,
    ) -> tuple[bool, str]:
        """Run edge-tts in a dedicated event loop (safe inside uvicorn/Proactor workers)."""
        from edge_tts import Communicate, SubMaker

        async def _run() -> None:
            communicate = Communicate(
                text,
                voice,
                rate=self.rate,
                pitch=self.pitch,
                boundary="WordBoundary",
            )
            submaker = SubMaker()
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            with open(audio_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        submaker.feed(chunk)
            if subtitle_path is not None:
                subtitle_path.write_text(submaker.get_srt(), encoding="utf-8")

        try:
            asyncio.run(_run())
        except Exception as exc:
            return False, str(exc)
        if audio_path.exists() and audio_path.stat().st_size > 0:
            return True, ""
        return False, "empty audio file"

    @staticmethod
    def _edge_safe_text(text: str, max_chars: Optional[int] = 280) -> str:
        cleaned = TTSService._sanitize_for_edge_tts(text)
        if not cleaned:
            return ""
        if max_chars is None or len(cleaned) <= max_chars:
            return cleaned
        head = cleaned[: max_chars - 1].rsplit(" ", 1)[0]
        return head or cleaned[:max_chars]

    async def _edge_tts_subprocess(
        self,
        text: str,
        voice: str,
        audio_path: Path,
        subtitle_path: Optional[Path] = None,
        *,
        max_chars: Optional[int] = 280,
        retries: int = 3,
        log_failures: bool = True,
    ) -> bool:
        """Synthesize with edge-tts in a worker thread (avoids Windows Proactor + CLI subprocess issues)."""
        text = self._edge_safe_text(text, max_chars=max_chars)
        if not text or not re.search(r"[\w\u00C0-\u1FFF]", text, re.UNICODE):
            logger.warning("Edge-TTS skipped: no speakable text after sanitize.")
            return False

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        voices_to_try = self._edge_voice_fallbacks(voice)

        last_err = ""
        for attempt in range(retries):
            for voice_name in voices_to_try:
                ok, last_err = await asyncio.to_thread(
                    self._edge_tts_sync_api,
                    text,
                    voice_name,
                    audio_path,
                    subtitle_path,
                )
                if ok:
                    return True

                if "NoAudioReceived" in last_err and len(text) > 60:
                    half = len(text) // 2
                    split_at = text.rfind(" ", 0, half)
                    if split_at > 20:
                        part_a = text[:split_at].strip()
                        part_b = text[split_at:].strip()
                        temp_a = audio_path.with_suffix(".part_a.mp3")
                        temp_b = audio_path.with_suffix(".part_b.mp3")
                        if await self._edge_tts_subprocess(
                            part_a,
                            voice_name,
                            temp_a,
                            subtitle_path=None,
                            max_chars=max_chars,
                            retries=2,
                            log_failures=False,
                        ) and await self._edge_tts_subprocess(
                            part_b,
                            voice_name,
                            temp_b,
                            subtitle_path=None,
                            max_chars=max_chars,
                            retries=2,
                            log_failures=False,
                        ):
                            list_file = audio_path.with_suffix(".concat.txt")
                            list_file.write_text(
                                "\n".join(
                                    f"file '{p.resolve().as_posix()}'"
                                    for p in (temp_a, temp_b)
                                ),
                                encoding="utf-8",
                            )
                            subprocess.run(
                                [
                                    "ffmpeg",
                                    "-y",
                                    "-f",
                                    "concat",
                                    "-safe",
                                    "0",
                                    "-i",
                                    str(list_file),
                                    "-c:a",
                                    "libmp3lame",
                                    "-q:a",
                                    "2",
                                    str(audio_path),
                                ],
                                check=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE,
                            )
                            temp_a.unlink(missing_ok=True)
                            temp_b.unlink(missing_ok=True)
                            list_file.unlink(missing_ok=True)
                            if audio_path.exists() and audio_path.stat().st_size > 0:
                                return True

            if attempt < retries - 1:
                await asyncio.sleep(1.5 * (attempt + 1))

        if log_failures:
            logger.error(
                "Edge-TTS failed after %d attempts (voice=%s, %d chars): %s",
                retries,
                voice,
                len(text),
                last_err[:800],
            )
        return False

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
        if self._use_local_tts() or self.provider == "f5tts":
            max_concurrency = 1
        elif settings.allow_network_tts():
            # Edge-TTS rate-limits aggressive parallel requests (NoAudioReceived).
            max_concurrency = min(max_concurrency, 2)

        logger.info(f"Generating TTS for {len(segments)} segments (concurrency={max_concurrency})")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        completed_count = 0
        completed_lock = asyncio.Lock()

        async def process_single_segment(i: int, seg: Dict[str, Any]) -> Path:
            async with semaphore:
                text = seg.get('translated_text', seg['text'])
                target_duration = seg['end'] - seg['start']
                
                raw_suffix = ".wav" if (self._use_local_tts() or self.provider == "f5tts") else ".mp3"
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
                end = seg['end']
                
                # Prevent negative gaps due to overlapping segments
                start = max(start, last_end)
                gap = start - last_end
                
                # If gap is significant (> 10ms), insert a silent file
                if gap > 0.01:
                    silence_path = temp_dir / f"gap_{i}.wav"
                    if VideoService.create_silence(gap, silence_path) and silence_path.exists():
                        f.write(f"file '{silence_path.absolute().as_posix()}'\n")
                
                # Verify segment file exists, if not, fill its duration with silence to maintain sync
                if not path.exists():
                    duration = max(0.01, end - start)
                    logger.warning(f"Segment {i} audio missing, filling {duration}s gap with silence.")
                    path = temp_dir / f"fallback_silence_{i}.wav"
                    VideoService.create_silence(duration, path)
                
                if path.exists():
                    f.write(f"file '{path.absolute().as_posix()}'\n")
                
                # Update last_end to the actual end of this segment
                last_end = max(end, start)
                
        logger.info(f"Concat list created at {output_list_file} with sync gaps.")
