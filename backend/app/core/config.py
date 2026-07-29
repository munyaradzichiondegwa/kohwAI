from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # App
    APP_NAME: str = "KohwAI"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "changeme"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://kohwai:secret@localhost:5432/kohwai"
    TIMESCALE_URL: str = "postgresql://kohwai:secret@localhost:5433/kohwai_ts"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    # Africa's Talking
    AT_API_KEY: str = ""
    AT_USERNAME: str = ""
    AT_SHORTCODE: str = "123"

    # EcoCash
    ECOCASH_API_KEY: str = ""
    ECOCASH_API_SECRET: str = ""

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-west-2"
    S3_MODEL_BUCKET: str = "kohwai-models"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # NASA POWER
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"

    # Sentry
    SENTRY_DSN: str = ""

    # AI Thresholds
    AI_CONFIDENCE_GATE: float = 0.70
    AI_AUDIO_TRIGGER_GATE: float = 0.75
    RISK_ALERT_THRESHOLD: int = 70
    OFFLINE_QUEUE_MAX: int = 50
    ALERT_DEDUP_HOURS: int = 6

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

settings = Settings()