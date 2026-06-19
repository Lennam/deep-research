import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend (pointing to backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    ZHIPUAI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    GLM_MODEL: str = "glm-4-flash" # default model, can be overridden by GLM_MODEL env var
    
    DEFAULT_MAX_DEPTH: int = 3
    DEFAULT_MAX_BREADTH: int = 3

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
