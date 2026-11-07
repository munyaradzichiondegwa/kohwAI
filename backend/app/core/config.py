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
    # Dev convenience only; honoured solely when ENVIRONMENT == "development".
    EXPOSE_DEV_OTP: bool = False

    # Parametric insurance rules (see modules/musika/insurance_service.py)
    INSURANCE_DROUGHT_THRESHOLD: int = 70        # drought_index (0-100) at/above which a day "qualifies"
    INSURANCE_MIN_CONSECUTIVE_DAYS: int = 5      # qualifying days in a row (PRD: >5 consecutive days)
    INSURANCE_WAITING_DAYS: int = 14             # enrol at least this long before the dry spell began
    INSURANCE_SEASON_START_MONTH: int = 11       # season runs Nov 1 .. Mar 31 of the following year
    INSURANCE_SEASON_END_MONTH: int = 3

    # Africa's Talking does not sign USSD callbacks. Comma-separated source IPs allowed to call
    # /ussd/callback. Outside development an empty list REJECTS all USSD traffic (otherwise anyone
    # could POST as any phone number and file reports / listings in that farmer's name).
    USSD_ALLOWED_IPS: str = ""

    # ── Alert dispatch (SMS) ────────────────────────────────────────────────
    ALERT_SMS_SEVERITIES: str = "red,darkRed"     # comma list; lower severities are in-app only (SMS costs money, spam erodes trust)
    ALERT_SMS_DAILY_CAP: int = 3                  # max alert SMS per farmer per day
    ALERT_MAX_AGE_HOURS: int = 48                 # never SMS an alert older than this (e.g. after a long outage)
    ALERT_SMS_BATCH: int = 100                    # recipients per gateway call
    ALERT_SMS_MAX_ATTEMPTS: int = 3
    RISK_MODEL_ALERTS_ENABLED: bool = False       # the livestock-risk heuristic is unvalidated: no farmer alerts until a vet signs off
    USSD_SERVICE_CODE: str = ""                   # e.g. "*123#" — shown in SMS text only when set

    # ── Accounts: PIN + consent ──────────────────────────────────────────────
    PIN_MAX_ATTEMPTS: int = 3
    PIN_LOCK_MINUTES: int = 30
    TERMS_VERSION: str = "2026-11-draft"          # bump when Terms/Privacy change: users are asked to re-accept

    # Real helpline numbers shown to farmers in emergencies. Left blank on purpose:
    # we never display a number nobody has verified. Set in .env once Agritex / Vet Services confirm them.
    VET_SERVICES_CONTACT: str = ""
    AGRITEX_CONTACT: str = ""

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
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3010", "http://localhost:3000", "http://localhost:8000"]

settings = Settings()