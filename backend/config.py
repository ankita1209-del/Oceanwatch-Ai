"""
OceanWatch AI — Application Configuration
==========================================
Reads settings from environment variables / .env file.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "OceanWatch AI"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change_me_in_production"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://oceanwatch:oceanwatch_secret@localhost:5432/oceanwatch"
    )

    # Redis (optional — for Celery tasks)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — React dev server
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # ML model paths
    DETECTION_MODEL_PATH: str = "models/detection/model.pt"
    PREDICTION_MODEL_PATH: str = "models/prediction/model.json"

    # Risk scoring weights (must sum to 1.0)
    W_AI_PREDICTION: float = 0.40
    W_CHL_ANOMALY: float = 0.20
    W_SST_ANOMALY: float = 0.15
    W_HISTORICAL_RISK: float = 0.15
    W_ENV_ANOMALY: float = 0.10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
