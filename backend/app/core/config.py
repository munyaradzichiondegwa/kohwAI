import os
from typing import List
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _secrets_dir() -> str | None:
    """Docker/Compose mounts secrets as files in /run/secrets (one file per secret, named exactly like the setting).
    Reading them here keeps passwords and keys out of environment variables, `docker inspect` and process listings."""
    explicit = os.environ.get("SECRETS_DIR")
    if explicit:
        return explicit
    return "/run/secrets" if os.path.isdir("/run/secrets") else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        secrets_dir=_secrets_dir(),
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

    # Connection parts (production): the URLs below are built from these when not given explicitly, so a password
    # held in a secret file can be used safely (special characters are URL-escaped).
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

    @model_validator(mode="after")
    def _compose_urls(self):
        given = self.model_fields_set          # anything the operator set explicitly always wins
        if self.POSTGRES_HOST and "DATABASE_URL" not in given:
            pw = quote(self.POSTGRES_PASSWORD, safe="")
            self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{pw}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        if self.REDIS_HOST:
            auth = f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""
            base = f"redis://{auth}{self.REDIS_HOST}:6379"
            if "REDIS_URL" not in given:
                self.REDIS_URL = f"{base}/0"
            if "CELERY_BROKER_URL" not in given:
                self.CELERY_BROKER_URL = f"{base}/0"
            if "CELERY_RESULT_BACKEND" not in given:
                self.CELERY_RESULT_BACKEND = f"{base}/1"
        return self

    def production_problems(self) -> tuple[list[str], list[str]]:
        """-> (errors, warnings). Errors make the API refuse to start outside development: each one is a
        misconfiguration that would expose farmers' data or let anyone act as anyone."""
        if self.ENVIRONMENT == "development":
            return [], []
        errors, warnings = [], []
        if self.SECRET_KEY in ("", "changeme") or len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be a random value of at least 32 characters (it signs every login token)")
        if self.DEBUG:
            errors.append("DEBUG must be off")
        if self.EXPOSE_DEV_OTP:
            errors.append("EXPOSE_DEV_OTP must be off (it returns login codes in API responses)")
        if ":secret@" in self.DATABASE_URL or ":changeme@" in self.DATABASE_URL:
            errors.append("the database is using a default password")
        if any(("localhost" in o or "127.0.0.1" in o or o.strip() == "*") for o in self.ALLOWED_ORIGINS):
            errors.append("ALLOWED_ORIGINS must list only your real https origin(s), not localhost or *")
        if not self.AT_API_KEY:
            warnings.append("AT_API_KEY is empty: login codes and alert SMS cannot be delivered, so nobody can sign in")
        if "@" not in self.REDIS_URL:
            warnings.append("Redis has no password")
        if not self.USSD_ALLOWED_IPS.strip():
            warnings.append("USSD_ALLOWED_IPS is empty: all USSD traffic will be rejected (fail-closed)")
        if not (self.VET_SERVICES_CONTACT.strip() and self.AGRITEX_CONTACT.strip()):
            warnings.append("helpline numbers (VET_SERVICES_CONTACT / AGRITEX_CONTACT) are not set: advice will say 'your nearest office'")
        return errors, warnings


settings = Settings()
