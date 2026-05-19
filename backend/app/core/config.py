import os
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "Dubify"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # Specific storage subdirs
    INPUT_DIR: Path = STORAGE_DIR / "input"
    TEMP_DIR: Path = STORAGE_DIR / "temp"
    OUTPUT_DIR: Path = STORAGE_DIR / "output"
    ARTIFACTS_DIR: Path = STORAGE_DIR / "artifacts"
    BGM_DIR: Path = STORAGE_DIR / "bgm"
    PIPER_MODELS_DIR: Path = MODELS_DIR / "piper"

    # Storage / security
    CLEANUP_TEMP: bool = True
    API_ADMIN_KEY: str = ""
    ENABLE_STUDIO_BGM: bool = True
    STUDIO_BGM_VOLUME: float = 0.15
    # Studio HTML scene render: auto (try HyperFrames then Playwright), playwright, hyperframes
    STUDIO_RENDER_ENGINE: str = "auto"
    
    # AI Config
    PROCESSING_ENGINE: str = "local"
    PROCESSING_MODE: str = "hybrid"
    DEFAULT_WHISPER_MODEL: str = "base"
    DEFAULT_NLLB_MODEL: str = "facebook/nllb-200-distilled-600M"
    # GPU (RTX / CUDA) — USE_GPU=true + CUDA PyTorch enables Whisper/NLLB on GPU; NVENC for FFmpeg
    USE_GPU: bool = True
    WHISPER_DEVICE: str = "auto"  # auto | cuda | cpu
    VIDEO_ENCODER: str = "auto"  # auto | nvenc | cpu
    NLLB_USE_GPU: bool = True
    OLLAMA_API_BASE: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "llama3"
    
    # Advanced Processing Features
    ENABLE_BGM_RETENTION: bool = False
    WHISPERX_API_URL: Optional[str] = None
    F5TTS_API_URL: Optional[str] = None
    
    # CORS (comma-separated origins, default allows localhost dev)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80"
    
    # API Keys (Loaded from .env)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    # LLM model id from llm_models catalog (e.g. groq:llama-3.3-70b-versatile) or "auto"
    LLM_MODEL: str = "auto"
    FAL_KEY: str = ""
    FAL_AI_API_KEY: str = ""
    PEXELS_API_KEY: str = ""
    DEEPL_API_KEY: str = ""
    OPENAI_TTS_MODEL: str = "tts-1"  # tts-1 or tts-1-hd
    OPENAI_TTS_VOICE: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    # Target voiceover length for AI Research Video (seconds)
    RESEARCH_VIDEO_TARGET_SECONDS: int = 45

    # Downloader settings
    YTDLP_COOKIE_FILE: str = ""
    YTDLP_COOKIES_FROM_BROWSERS: str = "chrome,edge,firefox"
    YTDLP_PROXY: str = ""
    YTDLP_SOCKET_TIMEOUT: int = 20
    YTDLP_USE_OAUTH2: bool = False
    DOUYIN_FALLBACK_API_BASE: str = ""
    DOUYIN_FALLBACK_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        extra = "ignore"

    def normalized_processing_engine(self) -> str:
        engine = (self.PROCESSING_ENGINE or "local").strip().lower()
        return engine if engine in {"local", "cloud"} else "local"

    def normalized_processing_mode(self) -> str:
        mode = (self.PROCESSING_MODE or "hybrid").strip().lower()
        return mode if mode in {"offline", "hybrid", "online"} else "hybrid"

    def default_translation_service(self) -> str:
        """Offline uses local NLLB; hybrid/online use Google Translate when network is allowed."""
        if self.normalized_processing_mode() == "offline":
            return "nllb"
        if self.normalized_processing_engine() == "cloud":
            return "google"
        return "google" if self.allow_network_downloads() else "nllb"

    def allow_cloud_llm(self) -> bool:
        return (
            self.normalized_processing_engine() == "cloud"
            and self.normalized_processing_mode() in {"hybrid", "online"}
        )

    def allow_network_tts(self) -> bool:
        return self.normalized_processing_mode() in {"hybrid", "online"}

    def allow_network_downloads(self) -> bool:
        return self.normalized_processing_mode() in {"hybrid", "online"}

    def use_gpu(self) -> bool:
        return bool(self.USE_GPU)

    def configured_cloud_providers(self) -> list[str]:
        providers: list[str] = []
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.GEMINI_API_KEY:
            providers.append("gemini")
        if self.GROQ_API_KEY:
            providers.append("groq")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        return providers

    def cloud_engine_ready(self) -> bool:
        return len(self.configured_cloud_providers()) > 0

    def cloud_engine_message(self) -> str:
        if self.normalized_processing_engine() != "cloud":
            return "Cloud engine is not selected."
        if self.cloud_engine_ready():
            providers = ", ".join(self.configured_cloud_providers())
            return f"Cloud engine is ready. Configured providers: {providers}."
        return "Cloud engine is selected but no supported API key is configured yet."

    def piper_available_models(self) -> list[str]:
        if not self.PIPER_MODELS_DIR.exists():
            return []

        models: list[str] = []
        for model_path in self.PIPER_MODELS_DIR.rglob("*.onnx"):
            config_path = Path(f"{model_path}.json")
            if config_path.exists():
                models.append(model_path.relative_to(self.PIPER_MODELS_DIR).as_posix())
        return sorted(models)

    def piper_ready(self) -> bool:
        return len(self.piper_available_models()) > 0

    def local_tts_message(self) -> str:
        if self.piper_ready():
            model_count = len(self.piper_available_models())
            return f"Offline Piper TTS is ready with {model_count} installed model(s)."
        return "Offline Piper TTS is not ready yet. Install at least one Piper voice model."

    def create_directories(self):
        """Ensure all required directories exist."""
        try:
            for path in [
                self.STORAGE_DIR,
                self.MODELS_DIR,
                self.INPUT_DIR,
                self.TEMP_DIR,
                self.OUTPUT_DIR,
                self.ARTIFACTS_DIR,
                self.BGM_DIR,
                self.PIPER_MODELS_DIR,
            ]:
                path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create directories: {e}")

settings = Settings()
settings.create_directories()
