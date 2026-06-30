import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend (pointing to backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    TAVILY_API_KEY: str = ""
    
    DEFAULT_MAX_DEPTH: int = 3
    DEFAULT_MAX_BREADTH: int = 3
    
    # RAG Settings
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5
    RAG_RELEVANCE_THRESHOLD: float = 0.35
    RAG_SIMILARITY_THRESHOLD: float = 0.82
    
    SQLITE_DB_PATH: str = str(BASE_DIR / "app.db")

    # Phase 4: Integration & Optimization settings
    LLM_INPUT_COST_PER_TOKEN: float = 0.15 / 1_000_000  # $0.15 per 1M tokens
    LLM_OUTPUT_COST_PER_TOKEN: float = 0.60 / 1_000_000 # $0.60 per 1M tokens
    SEARCH_COST_PER_CALL: float = 0.015                 # $0.015 per Tavily search
    DEFAULT_MAX_COST_BUDGET: float = 1.0                # Default budget limit of $1.00
    SCRAPER_CONCURRENCY_LIMIT: int = 5                  # Concurrency limit of pages scraped
    CACHE_SEARCH_TTL_DAYS: int = 1                      # Search cache validity duration
    CACHE_PAGE_TTL_DAYS: int = 7                        # Scraped page cache validity duration

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
