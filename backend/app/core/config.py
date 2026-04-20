import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dubify"
    API_V1_STR: str = "/api/v1"
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # Specific storage subdirs
    INPUT_DIR: Path = STORAGE_DIR / "input"
    TEMP_DIR: Path = STORAGE_DIR / "temp"
    OUTPUT_DIR: Path = STORAGE_DIR / "output"
    
    # AI Config
    DEFAULT_WHISPER_MODEL: str = "base"
    DEFAULT_NLLB_MODEL: str = "facebook/nllb-200-distilled-600M"
    
    # API Keys (Loaded from .env)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")

    def create_directories(self):
        """Ensure all required directories exist."""
        try:
            for path in [self.STORAGE_DIR, self.MODELS_DIR, self.INPUT_DIR, self.TEMP_DIR, self.OUTPUT_DIR]:
                path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create directories: {e}")

settings = Settings()
settings.create_directories()
