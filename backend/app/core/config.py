
import os
from pathlib import Path
from typing import List
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _secrets_dir() -> str | None:
    """Docker/Compose mounts secrets as files in /run/secrets
    (one file per secret, named exactly like the setting).

    Reading them here keeps passwords and keys out of environment
    variables, docker inspect and process listings.
    """
    explicit = os.environ.get("SECRETS_DIR")
    if explicit:
        return explicit

    return "/run/secrets" if os.path.isdir("/run/secrets") else None


# Resolve the project-root .env file independently of the working directory.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT_ENV),
        secrets_dir=_secrets_dir(),
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "KohwAI"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "changeme"
    DEBUG: bool = False

    # Dev convenience only; honoured solely when ENVIRONMENT == "development".
    EXPOSE_DEV_OTP: bool = False

    # Parametric insurance rules
    INSURANCE_DROUGHT_THRESHOLD: int = 70
    INSURANCE_MIN_CONSECUTIVE_DAYS: int = 5
    INSURANCE_WAITING_DAYS: int = 14
    INSURANCE_SEASON_START_MONTH: int = 11
    INSURANCE_SEASON_END_MONTH: int = 3

    # Africa's Talking USSD callback security
    USSD_ALLOWED_IPS: str = ""

    # Alert dispatch (SMS)
    ALERT_SMS_SEVERITIES: str = "red,darkRed"
    ALERT_SMS_DAILY_CAP: int = 3
    ALERT_MAX_AGE_HOURS: int = 48
    ALERT_SMS_BATCH: int = 100
    ALERT_SMS_MAX_ATTEMPTS: int = 3
    RISK_MODEL_ALERTS_ENABLED: bool = False
    USSD_SERVICE_CODE: str = ""

    # Accounts: PIN and consent
    PIN_MAX_ATTEMPTS: int = 3
    PIN_LOCK_MINUTES: int = 30
    TERMS_VERSION: str = "2026-11-draft"

    # Emergency contacts
    VET_SERVICES_CONTACT: str = ""
    AGRITEX_CONTACT: str = ""

    # Connection parts (production)
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "kohwai"
    POSTGRES_DB: str = "kohwai"
    POSTGRES_PASSWORD: str = ""
    REDIS_HOST: str = ""
    REDIS_PASSWORD: str = ""

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
    # Leave empty until Africa's Talking approves a sender ID / shortcode.
    AT_SHORTCODE: str = ""

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
    NASA_POWER_BASE_URL: str = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
    )

    # Sentry
    SENTRY_DSN: str = ""

    # AI Thresholds
    AI_CONFIDENCE_GATE: float = 0.70
    AI_AUDIO_TRIGGER_GATE: float = 0.75
    RISK_ALERT_THRESHOLD: int = 70
    OFFLINE_QUEUE_MAX: int = 50
    ALERT_DEDUP_HOURS: int = 6

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3010",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
    ]

    @model_validator(mode="after")
    def _compose_urls(self):
        given = self.model_fields_set

        if self.POSTGRES_HOST and "DATABASE_URL" not in given:
            pw = quote(self.POSTGRES_PASSWORD, safe="")
            self.DATABASE_URL = (
                f"postgresql://{self.POSTGRES_USER}:{pw}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        if self.REDIS_HOST:
            auth = (
                f":{quote(self.REDIS_PASSWORD, safe='')}@"
                if self.REDIS_PASSWORD
                else ""
            )
            base = f"redis://{auth}{self.REDIS_HOST}:6379"

            if "REDIS_URL" not in given:
                self.REDIS_URL = f"{base}/0"

            if "CELERY_BROKER_URL" not in given:
                self.CELERY_BROKER_URL = f"{base}/0"

            if "CELERY_RESULT_BACKEND" not in given:
                self.CELERY_RESULT_BACKEND = f"{base}/1"

        return self

    def production_problems(self) -> tuple[list[str], list[str]]:
        """Return (errors, warnings).

        Errors prevent the API from starting outside development.
        """
        if self.ENVIRONMENT == "development":
            return [], []

        errors, warnings = [], []

        if self.SECRET_KEY in ("", "changeme") or len(self.SECRET_KEY) < 32:
            errors.append(
                "SECRET_KEY must be a random value of at least 32 characters "
                "(it signs every login token)"
            )

        if self.DEBUG:
            errors.append("DEBUG must be off")

        if self.EXPOSE_DEV_OTP:
            errors.append(
                "EXPOSE_DEV_OTP must be off "
                "(it returns login codes in API responses)"
            )

        if ":secret@" in self.DATABASE_URL or ":changeme@" in self.DATABASE_URL:
            errors.append("the database is using a default password")

        if any(
            "localhost" in origin
            or "127.0.0.1" in origin
            or origin.strip() == "*"
            for origin in self.ALLOWED_ORIGINS
        ):
            errors.append(
                "ALLOWED_ORIGINS must list only your real https origin(s), "
                "not localhost or *"
            )

        if not self.AT_API_KEY:
            warnings.append(
                "AT_API_KEY is empty: login codes and alert SMS cannot be "
                "delivered, so nobody can sign in"
            )

        if "@" not in self.REDIS_URL:
            warnings.append("Redis has no password")

        if not self.USSD_ALLOWED_IPS.strip():
            warnings.append(
                "USSD_ALLOWED_IPS is empty: all USSD traffic will be rejected "
                "(fail-closed)"
            )

        if not (
            self.VET_SERVICES_CONTACT.strip()
            and self.AGRITEX_CONTACT.strip()
        ):
            warnings.append(
                "helpline numbers (VET_SERVICES_CONTACT / AGRITEX_CONTACT) "
                "are not set: advice will say 'your nearest office'"
            )

        return errors, warnings


settings = Settings()
