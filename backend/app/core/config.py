import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FraudLens"
    API_V1_STR: str = "" # Removed prefix as per frontend contract /api/*

    # Database
    SQLITE_DATABASE_URL: str = "sqlite:///C:/Users/hp/FraudLens/fraudlens.db"

    # Mode
    MODE: str = "live"  # 'fixture' or 'live'

    # LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Random seed for deterministic synthetic data
    RANDOM_SEED: int = 42

    class Config:
        case_sensitive = True

settings = Settings()
