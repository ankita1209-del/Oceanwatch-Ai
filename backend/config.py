"""Environment-based settings for the OceanWatch HAB API."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "OceanWatch AI"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    PREDICTION_MODEL_PATH: str = "models/prediction/xgboost_model.pkl"
    MODEL_METADATA_PATH: str = "models/prediction/model_metadata.json"
    ANOMALY_BASELINE_PATH: str = "data/processed/anomaly_baselines.json"
    ALERT_THRESHOLD: float = Field(default=61, ge=0, le=100)

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Synchronous connection string for Alembic and migrations."""
        if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://", 1
            )
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        return self.DATABASE_URL

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache

def get_settings() -> Settings:
    return Settings()
