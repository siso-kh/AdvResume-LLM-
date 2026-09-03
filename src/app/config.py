"""
Application Configuration
Settings loaded from environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "AI CV Screener"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database (SQLite for research phase)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/cv_screener.db"

    # LLM Configuration
    LLM_BASE_URL: str = ""  # Set via .env (routerByNara endpoint)
    LLM_API_KEY: str = ""   # Set via .env
    LLM_MODEL: str = "mistral-large"
    MAX_TOKENS: int = 1500
    TEMPERATURE: float = 0.1  # Low temperature for reproducible scoring

    # Scoring Configuration
    SCORE_INTERVIEW_THRESHOLD: int = 80
    SCORE_MAYBE_THRESHOLD: int = 50
    SCORE_REJECT_THRESHOLD: int = 0

    # Rate Limiting
    API_DELAY_SECONDS: float = 1.0  # Delay between API calls
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0

    # File Paths
    PROFILES_PATH: str = "data/synthetic/profiles.json"
    JOBS_DIR: str = "data/job_descriptions"
    RESULTS_DIR: str = "data/benchmarks"
    CV_DIR: str = "data/synthetic"
    ADVERSARIAL_DIR: str = "data/adversarial"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
