import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend (pointing to backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    TAVILY_API_KEY: str = ""
    
    DEFAULT_MAX_DEPTH: int = 3
    DEFAULT_MAX_BREADTH: int = 3

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
